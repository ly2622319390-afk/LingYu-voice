"""
行业专业词库系统 (Industry Lexicon System) — 核心模块

架构:
  用户行业选择 → 加载行业词库 → 注入ASR热词 → RAG检索 → 语义纠错
                      ↕
                缓存系统 (热词/词条/纠错/高频)
                      ↕
                用户学习 (误识别映射 → 词库更新)

设计原则:
  - 不要全量加载所有行业词库
  - 只加载用户选择的行业
  - 优先使用本地缓存，减少数据库查询
  - 用户词库 > 行业词库 > 公共词库
"""
import json
import hashlib
import logging
import re
import time
from typing import Optional

from backend.database import industry_lexicon_db as db
from backend.database import lexicon_db

logger = logging.getLogger("voice-input.industry-lexicon")


# ─── LLM 上下文感知纠错提示词 ──────────────────────────────────

_LLM_CORRECTION_PROMPT = """你是一个语音识别纠错专家。用户说话经过 ASR 语音识别后，可能存在同音/近音误识别。你需要根据**上下文语义**判断是否需要纠正。

## 输入
原始文本: "{text}"
{industry_context}

## 纠错规则
1. **读音相同但词义不同的词**不要纠正。例如：
   - "苹果很好吃" → 不要改（说的是水果）
   - "苹果发布了新手机" → 不要改（说的是公司，不是水果）
   - "克劳德" 在 AI 语境下 → "Claude"（专业名词）
   - "克劳德" 在普通语境下 → 不要改（可能是外国人名）

2. **英文技术术语**的常见误识别要纠正：
   - "拍 touch" → "PyTorch"
   - "lang chain" → "LangChain"
   - "RAG" 保持大写
   - "咧哥西" → "RAG 技术"

3. **只纠正明显是 ASR 误识别的专业词汇**，不要随意改普通词

4. **注意上下文**：
   - 如果在讨论 AI/技术话题 → 优先纠正技术术语
   - 如果在讨论日常生活 → 不要过度纠正

## 输出格式（只返回 JSON，不要其他文字）
```json
{{
  "corrected": "纠正后的完整文本",
  "corrections": [
    {{
      "original": "原文中被替换的部分",
      "corrected": "纠正后的词",
      "reason": "纠正原因"
    }}
  ]
}}
```"""


class IndustryLexiconSystem:
    """行业专业词库系统 — 核心入口"""

    def __init__(self):
        # 当前加载的行业
        self._active_industries: list[str] = []

        # ─── 缓存 ───
        self._hotword_cache: list[str] = []           # 热词缓存
        self._hotword_cache_time = 0
        self._alias_cache: dict[str, str] = {}         # 误识别映射缓存
        self._alias_cache_time = 0
        self._word_cache: dict[str, list[dict]] = {}   # 行业词条缓存 {industry: [...]}
        self._word_cache_time: dict[str, float] = {}
        self._user_correction_cache: dict[str, str] = {}  # 用户修正映射缓存
        self._user_cache_time = 0
        self._high_freq_cache: list[str] = []          # 高频词缓存
        self._high_freq_time = 0

        # 缓存 TTL（秒）
        self.CACHE_TTL = {
            "hotword": 60,        # 热词缓存 1 分钟
            "alias": 120,         # 误识别映射 2 分钟
            "word": 300,          # 词条缓存 5 分钟
            "user_correction": 60, # 用户修正 1 分钟
            "high_freq": 120,     # 高频词 2 分钟
        }

    # ─── 行业选择 ────────────────────────────────────────────────

    def select_industries(self, user_id: str, industries: list[str]):
        """用户选择行业 → 更新并加载对应词库"""
        db.set_user_industries(user_id, industries)
        self._active_industries = industries
        self._clear_cache()
        logger.info(f"用户 {user_id} 选择行业: {industries}")

    def get_selected_industries(self, user_id: str) -> list[str]:
        """获取用户已选择的行业"""
        industries = db.get_user_industries(user_id)
        self._active_industries = industries
        return industries

    # ─── 热词获取 ────────────────────────────────────────────────

    def get_hotwords(self, user_id: str = "default", force_refresh: bool = False) -> list[str]:
        """
        获取当前行业的 ASR 热词列表

        优先级: 用户词库高频词 > 行业高频词 > 行业普通词
        目标: < 200ms
        """
        now = time.time()
        if not force_refresh and self._hotword_cache and (now - self._hotword_cache_time) < self.CACHE_TTL["hotword"]:
            return self._hotword_cache

        industries = self._active_industries or self.get_selected_industries(user_id)
        if not industries:
            return []

        # 1. 从行业词库获取热词
        industry_words = db.get_words_for_hotwords(industries)

        # 2. 从用户词库获取高频词（优先级更高）
        user_words = lexicon_db.get_all_words(user_id)
        user_high_freq = sorted(user_words, key=lambda w: -w.get("usage_count", 0))[:30]

        # 3. 合并去重
        seen = set()
        hotwords = []

        # 用户高频词优先
        for w in user_high_freq:
            word = w["word"]
            if word not in seen:
                seen.add(word)
                hotwords.append(word)

        # 行业词补充（按 weight 排序）
        for w in industry_words:
            word = w["word"]
            if word not in seen:
                seen.add(word)
                hotwords.append(word)

        # 限制数量
        hotwords = hotwords[:200]

        self._hotword_cache = hotwords
        self._hotword_cache_time = now
        logger.debug(f"热词加载完成: {len(hotwords)} 个 (行业: {industries})")
        return hotwords

    # ─── ASR 纠错 ────────────────────────────────────────────────

    def correct_text(self, text: str, user_id: str = "default") -> dict:
        """
        ASR 文本纠错 — 基于行业词库 + 用户修正映射

        性能优化:
          - jieba.lcut() 只调用一次，复用切词结果
          - wrong not in lower_text 快速剪枝，跳过 99% 不相关的别名
        """
        if not text:
            return {"original": text, "corrected": text, "corrections": []}

        corrections = []
        corrected = text
        lower_text = text.lower()

        # 预计算 jieba 切词（只做一次）
        tokens = self._segment_chinese(lower_text)

        # Step 1: 用户修正映射
        user_map = self._get_user_correction_map(user_id)
        for wrong, correct in sorted(user_map.items(), key=lambda x: -len(x[0])):
            if wrong not in lower_text:
                continue
            if self._is_word_boundary_match(lower_text, wrong, tokens):
                idx = lower_text.find(wrong)
                actual_wrong = text[idx:idx + len(wrong)]
                if actual_wrong in corrected:
                    corrected = corrected.replace(actual_wrong, correct, 1)
                    corrections.append({"original": actual_wrong, "corrected": correct, "source": "user_learning", "confidence": 0.95})

        # Step 2: 行业词库 aliases 映射
        alias_map = self._get_alias_map(user_id)
        for wrong, correct in sorted(alias_map.items(), key=lambda x: -len(x[0])):
            if correct in corrected:
                continue
            # 快速剪枝：wrong 不在 lower_text 中就跳过（避免对 6000+ 别名逐个做正则）
            if wrong not in lower_text:
                continue
            if self._is_word_boundary_match(lower_text, wrong, tokens):
                idx = lower_text.find(wrong)
                actual_wrong = text[idx:idx + len(wrong)]
                if actual_wrong in corrected:
                    corrected = corrected.replace(actual_wrong, correct, 1)
                    corrections.append({"original": actual_wrong, "corrected": correct, "source": "industry_lexicon", "confidence": 0.85})

        return {"original": text, "corrected": corrected, "corrections": corrections, "correction_count": len(corrections)}

    @staticmethod
    def _segment_chinese(text: str) -> set[str]:
        """预切词，返回 token set（只做一次 jieba.lcut）"""
        if not re.search(r'[一-鿿]', text):
            return set()
        try:
            import jieba
            return set(jieba.lcut(text))
        except ImportError:
            return set()

    def correct_text_llm(self, text: str, user_id: str = "default") -> dict:
        """
        ASR 文本纠错 — LLM 增强版（上下文感知）

        用大模型判断：哪些"读音相近"的词应该被替换，
        避免"克劳德→Claude"、"lang chain→LangChain"等误判。

        回退: 当 LLM 不可用时自动降级为 correct_text()
        """
        if not text:
            return {"original": text, "corrected": text, "corrections": []}

        try:
            from backend.config import settings
            if not settings.LLM_ENABLED or not settings.ANTHROPIC_API_KEY:
                return self.correct_text(text, user_id)

            import anthropic

            # 收集上下文: 当前活跃行业的词条
            industry_context = ""
            industries = self._active_industries or self.get_selected_industries(user_id)
            if industries:
                industry_context = "当前行业: " + ", ".join(industries)

            prompt = _LLM_CORRECTION_PROMPT.format(
                text=text,
                industry_context=industry_context,
            )

            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            response = client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content[0].text.strip()

            # 解析 JSON 结果
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                return self._fallback_correction(text, user_id)

            result = json.loads(json_match.group())
            return {
                "original": text,
                "corrected": result.get("corrected", text),
                "corrections": result.get("corrections", []),
                "correction_count": len(result.get("corrections", [])),
                "mode": "llm",
            }
        except Exception as e:
            logger.warning(f"LLM 纠错失败，降级到规则纠错: {e}")
            return self.correct_text(text, user_id)

    def _fallback_correction(self, text: str, user_id: str) -> dict:
        """LLM 解析失败时的降级处理"""
        return self.correct_text(text, user_id)

    # ─── 整词匹配 ────────────────────────────────────────────────

    def _is_word_boundary_match(self, lower_text: str, wrong: str,
                                 tokens: set[str] | None = None) -> bool:
        """
        判断 wrong 是否在 lower_text 中以"完整词"形式出现。

        规则:
          - 英文短词（≤2字母）: 必须 \b 边界匹配，完全匹配
          - 英文长词（≥3字母）: 要求 \b 边界或后跟非字母
          - 中文词（≥2字）: 用 jieba 分词后检查是否完整 token
          - 中文短词（1字）: 不匹配（避免单字误伤）
        """
        if not wrong or len(wrong) < 1:
            return False

        # 中文短词（单字）不参与匹配
        if re.match(r'^[一-鿿]$', wrong):
            return False

        # 中文词（2字以上）: 用预切词的 tokens set 做 O(1) 查找
        if re.match(r'^[一-鿿\w]{2,}$', wrong):
            if tokens and wrong in tokens:
                return True
            # 检查是否被中文/标点包围或独立出现
            pattern = re.compile(
                rf'(?<=[一-鿿\s，。、；：？！）】」\'"]){re.escape(wrong)}(?=[一-鿿\s，。、；：？！（【「\'"])'
                rf'|^{re.escape(wrong)}(?=[一-鿿\s，。、；：？！（【「\'"])'
                rf'(?<=[一-鿿\s，。、；：？！）】」\'"]){re.escape(wrong)}$'
            )
            if pattern.search(lower_text):
                return True
            # 最终兜底：直接子串匹配（只要不是其他词的一部分）
            return wrong in lower_text

        # 英文/数字词
        if re.match(r'^[a-z0-9]+$', wrong):
            if len(wrong) <= 2:
                # 短词（如 "ai"）: 必须 \b 严格边界
                return bool(re.search(rf'\b{re.escape(wrong)}\b', lower_text))
            else:
                # 长词: 宽松边界（允许 -_ 等连接符，也兼容中文前后文）
                return bool(re.search(
                    rf'(?:^|[\s,.;:!?\'"\(\)\[\]{{}}一-鿿]){re.escape(wrong)}(?:$|[\s,.;:!?\'"\(\)\[\]{{}}一-鿿])',
                    lower_text
                ))

        # 混合词（如 "lang chain"）: 直接子串搜索 + 前后边界
        return wrong in lower_text

    # ─── RAG 检索 ────────────────────────────────────────────────

    def retrieve_candidates(self, text: str, user_id: str = "default", top_k: int = 5) -> list[dict]:
        """
        从行业词库中检索匹配的候选词

        当前: 基于文本匹配 + 权重排序
        后续: embedding 向量检索

        目标: < 150ms
        """
        industries = self._active_industries or self.get_selected_industries(user_id)
        if not text or not industries:
            return []

        candidates = []
        words = self._extract_keywords(text)

        for industry in industries:
            industry_words = self._get_cached_words(industry)
            for word_entry in industry_words:
                word = word_entry["word"]
                for kw in words:
                    score = self._match_score(kw, word)
                    if score > 0.5:
                        candidates.append({
                            "word": word,
                            "keyword": kw,
                            "score": round(score, 3),
                            "industry": industry,
                            "type": word_entry.get("type", ""),
                            "weight": word_entry.get("weight", 0.8),
                            "description": word_entry.get("description", ""),
                        })

        # 去重排序
        seen = set()
        unique = []
        for c in sorted(candidates, key=lambda x: -x["score"]):
            key = c["word"]
            if key not in seen:
                seen.add(key)
                unique.append(c)

        return unique[:top_k]

    # ─── 用户学习 ────────────────────────────────────────────────

    def learn_correction(self, user_id: str, wrong: str, correct: str):
        """
        用户修正 → 记录到误识别映射 + 自动加入用户词库

        触发条件: 用户手动将某个识别结果改为正确的词
        """
        if not wrong or not correct:
            return

        # 记录误识别映射
        db.record_misrecognition(user_id, wrong, correct)

        # 同步加入用户词库
        lexicon_db.add_word(user_id, correct, source="用户修正")

        # 清除用户修正缓存，下次重新加载
        self._user_cache_time = 0

        logger.info(f"用户 {user_id} 修正: '{wrong}' → '{correct}'")

    # ─── 词库导入 ────────────────────────────────────────────────

    def import_words(self, words: list[dict]) -> dict:
        """
        批量导入词条到行业词库

        word 格式: {"word": "...", "industry": "...", "aliases": [...], "weight": 0.9, ...}
        """
        count = db.add_industry_words(words)
        self._clear_cache()
        return {"imported": count}

    def get_industry_list(self) -> list[str]:
        """获取所有可用行业"""
        return db.get_all_industries()

    def get_industry_words(self, industry: str) -> list[dict]:
        """获取指定行业的完整词条"""
        return db.get_industry_words(industry)

    def search_words(self, keyword: str, industry: str = "") -> list[dict]:
        """搜索行业词条"""
        return db.search_industry_words(keyword, industry)

    # ─── 缓存管理 ────────────────────────────────────────────────

    def _get_user_correction_map(self, user_id: str) -> dict[str, str]:
        """获取用户修正映射（带缓存）"""
        now = time.time()
        if not self._user_correction_cache or (now - self._user_cache_time) > self.CACHE_TTL["user_correction"]:
            self._user_correction_cache = db.get_user_correction_map(user_id)
            self._user_cache_time = now
        return self._user_correction_cache

    def _get_alias_map(self, user_id: str = "default") -> dict[str, str]:
        """获取行业词库误识别映射（带缓存）

        修复: 如果内存中的 _active_industries 为空（重启后），
        自动从数据库回退读取用户已选的行业。
        """
        now = time.time()
        if not self._alias_cache or (now - self._alias_cache_time) > self.CACHE_TTL["alias"]:
            industries = self._active_industries or self.get_selected_industries(user_id)
            self._alias_cache = db.get_alias_map(industries)
            self._alias_cache_time = now
        return self._alias_cache

    def _get_cached_words(self, industry: str) -> list[dict]:
        """获取行业词条（带缓存）"""
        now = time.time()
        last_time = self._word_cache_time.get(industry, 0)
        if industry not in self._word_cache or (now - last_time) > self.CACHE_TTL["word"]:
            self._word_cache[industry] = db.get_industry_words(industry)
            self._word_cache_time[industry] = now
        return self._word_cache[industry]

    def _clear_cache(self):
        """清除所有缓存"""
        self._hotword_cache = []
        self._hotword_cache_time = 0
        self._alias_cache = {}
        self._alias_cache_time = 0
        self._word_cache = {}
        self._word_cache_time = {}
        self._high_freq_cache = []
        self._high_freq_time = 0

    # ─── 辅助方法 ────────────────────────────────────────────────

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """从文本中提取关键词"""
        import re
        # 提取英文词和中文词
        words = re.findall(r'[a-zA-Z]+[a-zA-Z0-9._#]*|[一-鿿\w]{2,}', text)
        return [w for w in words if len(w) >= 2]

    @staticmethod
    def _match_score(query: str, term: str) -> float:
        """计算查询词与词条的相关度"""
        q = query.lower().strip()
        t = term.lower().strip()

        if q == t:
            return 1.0
        if q in t or t in q:
            return 0.85
        # 计算公共子串比例
        common = 0
        for i in range(min(len(q), len(t))):
            if q[i] == t[i]:
                common += 1
            else:
                break
        if common > 0 and common / max(len(q), len(t)) > 0.5:
            return 0.6 + 0.2 * (common / max(len(q), len(t)))
        return 0.0


# 全局单例
_industry_lexicon_system: Optional[IndustryLexiconSystem] = None


def get_industry_lexicon_system() -> IndustryLexiconSystem:
    global _industry_lexicon_system
    if _industry_lexicon_system is None:
        _industry_lexicon_system = IndustryLexiconSystem()
    return _industry_lexicon_system
