"""文档术语自动提取服务

工作模式:
  1. LLM 模式 — 调用大模型（Anthropic/OpenAI）提取专业名词、专有词汇
  2. MVP 模式 — 基于 jieba 分词 + 规则提取（无需 API Key，开箱即用）
"""
import json
import logging
import re
from typing import Optional

logger = logging.getLogger("voice-input.term-extraction")

# ─── 通用词过滤 ────────────────────────────────────────────────
_COMMON_WORDS = {
    "我们", "他们", "她们", "它们", "你们", "咱们", "大家",
    "可以", "没有", "这个", "那个", "什么", "一个", "进行",
    "通过", "使用", "需要", "其中", "之后", "包括", "以及",
    "或者", "不是", "就是", "因为", "所以", "已经", "可能",
    "如果", "比较", "成为", "也是", "目前", "同时", "方面",
    "情况", "问题", "工作", "主要", "能够", "相关", "具有",
    "用于", "基于", "提供", "支持", "实现", "开发", "应用",
    "系统", "数据", "信息", "服务", "管理", "技术", "产品",
    "方式", "内容", "结果", "方法", "过程", "能力", "功能",
    "用户", "文档", "文件", "代码", "模型", "框架", "接口",
    "类型", "名称", "页面", "项目", "版本", "时间", "工具",
    "行业", "领域", "场景", "业务", "平台", "资源", "方案",
    "网络", "协议", "标准", "格式", "结构", "组件", "模块",
    "策略", "中心", "任务", "角色", "目标", "计划", "报告",
    "分析", "设计", "测试", "发布", "更新", "修改", "配置",
    "运行", "启动", "停止", "创建", "删除", "增加", "减少",
    "输入", "输出", "访问", "处理", "控制", "选择", "设置",
    "建议", "指标", "水平", "来源", "对象", "状态", "权限",
    "培训", "笔记", "帮助", "视图", "尺寸", "高级", "基础",
    "核心", "全新", "创新", "领先", "智能", "真实", "价值",
    "正确", "完整", "直接", "简单", "复杂", "快速", "稳定",
    "安全", "开放", "共享", "综合", "全面", "深入", "强大",
    "实际", "一定", "更多", "一些", "怎么", "自己", "这里",
    "那里", "知识", "经验", "学习", "训练", "研究", "教育",
    "中文", "英文", "语言", "文本", "图片", "视频", "音频",
    "市场", "客户", "体验", "质量", "效率", "成本",
    "费用", "价格", "预算", "团队", "组织",
    "机构", "部门", "小组", "委员会", "办公室",
    "目标", "关系", "制度",
    "只是", "还是", "而是", "但是",
    "然而", "虽然", "由于",
    "为了", "除了", "关于", "对于", "按照", "根据", "经过",
    "比如", "例如", "等等",
    "先前", "此外", "总之",
    "特别", "尤其", "非常", "相当",
    "能够", "应该", "必须", "将会",
    "正在", "仍然",
    "一般", "通常", "往往", "经常", "有时", "偶尔",
    "很大", "很小", "很多", "很少", "较多", "较少", "大量",
    "部分", "全部", "所有", "每个", "任何", "各个", "整个",
    "范围", "程度", "层次", "环节", "步骤",
    "运营", "维护", "升级", "优化", "改进", "增强",
    "准备", "开始", "结束", "完成", "成功", "失败", "取消",
    "执行", "实施", "开展", "推进", "促进", "推动",
    "建立", "形成", "构成", "组成", "属于", "具备", "拥有",
    "代表", "表示", "表明", "说明", "解释", "描述", "定义",
    "包含", "涵盖", "涉及", "有关", "围绕", "针对",
    "遵循", "遵守", "符合", "满足", "适应", "匹配", "兼容",
    "客服", "反馈", "评价", "评分", "排行", "排名",
    "规则", "手段", "途径",
}

# ─── LLM 提示词 ────────────────────────────────────────────────

EXTRACTION_PROMPT_TEMPLATE = """你是一个专业术语提取专家。从以下文档内容中，提取出所有专业名词、专有词汇。

需要提取的类别包括：
1. **技术术语**：专业技术名词、算法、框架、协议、标准（如：Transformer、RAG、TCP/IP）
2. **公司/组织名称**：企业、机构、团队（如：字节跳动、OpenAI、IEEE）
3. **人名**：领域专家、作者、关键人物（如：爱因斯坦、Geoffrey Hinton）
4. **项目/产品名称**：项目代号、产品名、版本号（如：Manus、通义千问、GPT-4o）
5. **品牌/商标**：产品品牌、服务名（如：飞书、钉钉、GitHub Copilot）
6. **专业缩写**：行业通用的英文缩写（如：NLP、ASR、LLM、KPI）
7. **特定领域词汇**：文档所属领域的核心概念（如：联邦学习、向量数据库、零信任架构）

提取规则：
- 只提取真正有专业价值的词汇，不要提取普通日常用词
- 英文术语保持原文大小写
- 中文术语使用标准名称
- 短缩写（2-5个字母大写）应当保留
- 合并相同含义的术语

文档内容：
```
{document_text}
```

请以 JSON 数组格式返回结果，每个元素包含 "term" 和 "type" 字段，type 为以下之一：技术术语、公司名称、人名、产品名称、品牌、专业缩写、领域概念。
只返回 JSON 数组，不要其他文字说明。"""


def extract_terms_llm(text: str, doc_type: str = "") -> list[dict]:
    """使用大模型（Anthropic）提取术语"""
    try:
        import anthropic
        from backend.config import settings

        if not settings.ANTHROPIC_API_KEY:
            logger.warning("未配置 ANTHROPIC_API_KEY，回退到规则提取")
            return _extract_terms_rule(text)

        prompt = EXTRACTION_PROMPT_TEMPLATE.format(document_text=text[:8000])
        if doc_type:
            prompt = prompt.replace("特定领域词汇", f"特定领域词汇（尤其关注 {doc_type} 领域）")

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text

        # 解析 JSON
        json_match = re.search(r'\[.*?\]', content, re.DOTALL)
        if json_match:
            terms = json.loads(json_match.group())
            logger.info(f"LLM 提取术语 {len(terms)} 个")
            return terms
        return []
    except ImportError:
        logger.warning("anthropic 库未安装，回退到规则提取")
        return _extract_terms_rule(text)
    except Exception as e:
        logger.error(f"LLM 提取失败: {e}")
        return _extract_terms_rule(text)


def extract_terms(text: str, doc_type: str = "", use_llm: bool = False) -> list[dict]:
    """提取文档中的专业术语（入口函数）"""
    text = text.strip()
    if not text:
        return []

    if use_llm:
        try:
            from backend.config import settings
            if settings.LLM_ENABLED:
                return extract_terms_llm(text, doc_type)
        except Exception:
            pass

    return _extract_terms_rule(text)


# ─── MVP 模式：基于规则的术语提取 ─────────────────────────────────

# 中文专名后缀模式（修正：只匹配 2-6 字 + 专业后缀）
_CHINA_SPECIAL_SUFFIX = re.compile(
    r'[一-鿿]{2,6}(?:模型|算法|系统|框架|平台|引擎|协议|标准|工具|库|网络|架构|'
    r'数据库|接口|组件|模块|方案|方法|理论|体系|协议|服务器|客户端|编译器)'
)

# 英文专名模式（CamelCase、版本号等）

# 英文专名模式（CamelCase、版本号等）
_EN_TERM = re.compile(
    r'(?:[A-Z][a-z]+[A-Z][a-zA-Z]*|'     # CamelCase: LangChain, Transformer
    r'[A-Z]{2,}(?:[-/][A-Z0-9]+)*|'       # ALL CAPS: ASR, NLP, TCP/IP
    r'[A-Za-z][a-zA-Z0-9._-]+[A-Z][a-z]+)'  # MixedCase: GPT-4o, GitHub Copilot
)

# 引号括起来的术语
_QUOTED_TERM = re.compile(r'[「『""]([一-鿿A-Za-z0-9+/_-]{2,})[」』""]')

# 英文缩写（2-6个大写字母）
_ABBREVIATION = re.compile(r'(?<![A-Za-z])[A-Z]{2,6}(?![A-Za-z])')


def _extract_terms_rule(text: str) -> list[dict]:
    """基于规则的术语提取（MVP 模式，无需 API Key）"""
    seen = set()
    terms = []

    def add(term: str, term_type: str):
        key = term.lower().strip()
        if key not in seen and len(term.strip()) >= 2:
            # 过滤纯数字、纯标点、单字、过长短语
            if re.match(r'^[\d\s.,;:!?。，；：！？、-]+$', term.strip()):
                return
            if len(term.strip()) > 12:
                return
            if term.strip() in _COMMON_WORDS:
                return
            seen.add(key)
            terms.append({"term": term.strip(), "type": term_type})

    # 1. 引号术语
    for m in _QUOTED_TERM.finditer(text):
        add(m.group(1), "领域概念")

    # 2. 英文 CamelCase 术语（在 jieba 之前，避免被分词切碎）
    for m in _EN_TERM.finditer(text):
        word = m.group()
        if word.lower() not in {"the", "this", "that", "with", "from", "have", "will", "would", "could",
                                 "should", "about", "which", "their", "there", "where", "after", "other",
                                 "using", "based", "model", "data", "text", "file", "code", "user",
                                 "system", "time", "work", "part", "type", "name", "page", "size",
                                 "info", "note", "help", "view", "show", "must", "also", "than", "then",
                                 "case", "all", "any", "can", "see", "new", "use", "way", "say", "may",
                                 "well", "such", "some", "same", "here", "over", "long", "high", "down",
                                 "like", "just", "more", "most", "make", "made", "take", "come", "done",
                                 "many", "very", "need", "find", "give", "know", "been", "when", "what",
                                 "each", "both", "much", "back", "next", "than", "then", "also", "only",
                                 "top", "set", "run", "end", "add", "get", "put", "let", "say", "try",
                                 "way", "own", "yet", "now", "too", "two", "one", "who", "how", "own"}:
            add(word, "技术术语")

    # 3. 英文缩写
    for m in _ABBREVIATION.finditer(text):
        word = m.group()
        if word not in {"THE", "THIS", "THAT", "WITH", "FROM", "HAVE", "WILL", "WOULD",
                        "ABOUT", "WHICH", "THERE", "WHERE", "AFTER", "OTHER", "ALSO",
                        "THAN", "THEN", "WHEN", "WHAT", "BEEN", "BEING", "MUST", "ONLY"}:
            add(word, "专业缩写")

    # 4. jieba 分词提取（专有名词 + 中文专名后缀）
    try:
        import jieba
        import jieba.posseg as pseg

        words = pseg.cut(text)
        for word, flag in words:
            w = word.strip()
            if len(w) < 2:
                continue
            if flag in ("nr", "nr1", "nr2", "nrj"):
                add(w, "人名")
            elif flag == "nt":
                add(w, "公司名称")
            elif flag in ("nz", "j"):
                add(w, "领域概念")
            elif flag == "ns":
                add(w, "领域概念")
            elif flag == "x" and re.match(r'^[A-Za-z0-9+/_-]{2,}$', w):
                add(w, "技术术语")
            elif 2 <= len(w) <= 8 and _has_tech_suffix(w):
                add(w, "技术术语")
    except ImportError:
        # jieba 不可用时用正则回退
        for m in _CHINA_SPECIAL_SUFFIX.finditer(text):
            add(m.group(), "技术术语")

    # 5. 频率分析：全文出现 2+ 次的关键词
    _add_high_freq_terms(text, terms, seen, add)

    # 去重排序
    type_priority = {"技术术语": 0, "专业缩写": 1, "公司名称": 2, "领域概念": 3, "产品名称": 4, "人名": 5}
    terms.sort(key=lambda t: (type_priority.get(t["type"], 9), t["term"]))

    logger.info(f"规则提取术语 {len(terms)} 个")
    return terms


def _has_tech_suffix(word: str) -> bool:
    """判断中文词是否含有技术后缀"""
    suffixes = [
        "模型", "算法", "系统", "框架", "平台", "引擎", "协议", "标准",
        "工具", "数据库", "接口", "组件", "模块", "方案", "方法", "理论",
        "体系", "服务器", "客户端", "编译器", "网络", "架构",
        "语言", "文件", "格式", "协议", "规范", "策略",
    ]
    for s in suffixes:
        if word.endswith(s):
            return True
    return False


def _add_high_freq_terms(text: str, terms: list, seen: set, add):
    """频率分析提取：2-6字词出现2次以上"""
    try:
        import jieba
        words = jieba.lcut(text)
        freq = {}
        for w in words:
            w = w.strip()
            if 2 <= len(w) <= 6:
                freq[w] = freq.get(w, 0) + 1

        # 过滤普通词汇
        common_words = set()
        try:
            from jieba.analyse import get_textrank_tags
            # 用 TextRank 区分关键词和普通词
            keywords = set(get_textrank_tags(text, topK=50))
        except Exception:
            keywords = set()

        for word, count in freq.items():
            if count >= 2 and word not in seen and len(word) >= 2:
                if word in _COMMON_WORDS:
                    continue
                if word in keywords or re.search(r'[一-鿿]', word):
                    if word not in _COMMON_WORDS:
                        add(word, "领域概念")
    except ImportError:
        pass
