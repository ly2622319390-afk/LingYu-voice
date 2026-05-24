"""
专业词纠错模块 — AI 架构第 3 项

架构:
  ASR输出 → 用户词库召回 → 行业词库召回 → 语义排序 → 候选词

当前 MVP: 基于本地词库的匹配纠错
后续 V2:    接入 RAG + 小模型语义排序
"""

import re
from typing import Optional


class TermCorrector:
    """
    专业词纠错器

    匹配 ASR 结果中的可疑词汇，对照用户词库/行业词库修正

    Usage:
        corrector = TermCorrector()
        result = corrector.correct("今天我们讨论langchain", user_lexicon=[...], industry_lexicon=[...])
        # -> {"text": "今天我们讨论LangChain", "corrections": [...], "uncertain": []}
    """

    def __init__(self):
        self._term_patterns: list[dict] = []
        self._semantic_model = None  # 预留语义排序模型

    def correct(self, text: str,
                user_lexicon: list[dict],
                industry_lexicon: list[dict] = None) -> dict:
        """
        执行纠错

        返回:
        {
            "text": "修正后文本",
            "corrections": [{"original": "...", "corrected": "...", "confidence": 0.95}],
            "uncertain": [{"word": "...", "suggestions": [...], "position": 0}]
        }
        """
        user_lexicon = user_lexicon or []
        industry_lexicon = industry_lexicon or []

        # 1. 构建词库索引
        term_map = {}
        for w in user_lexicon:
            key = w["word"].lower()
            term_map[key] = {"word": w["word"], "type": w.get("word_type", ""),
                             "confidence": w.get("confidence", 0.8), "source": "user"}
        for w in industry_lexicon:
            key = w["word"].lower()
            if key not in term_map:
                term_map[key] = {"word": w["word"], "type": w.get("word_type", ""),
                                 "confidence": w.get("confidence", 0.9), "source": "industry"}

        corrections = []
        uncertain = []

        # 2. 对 ASR 结果中的每个词进行匹配
        words = re.findall(r'[\w]+', text)
        for word in words:
            word_lower = word.lower()
            if word_lower in term_map:
                entry = term_map[word_lower]
                if entry["word"] != word:
                    corrections.append({
                        "original": word,
                        "corrected": entry["word"],
                        "confidence": entry["confidence"],
                        "source": entry["source"]
                    })
            else:
                # 不在词库中 -> 检查是否可能是专有名词
                if self._looks_like_proper_term(word):
                    uncertain.append({
                        "word": word,
                        "suggestions": [],
                        "position": text.find(word)
                    })

        # 3. 应用高置信度修正
        final_text = text
        for c in corrections:
            if c["confidence"] >= 0.85:
                final_text = final_text.replace(c["original"], c["corrected"], 1)

        return {
            "text": final_text,
            "corrections": corrections,
            "uncertain": uncertain
        }

    def _looks_like_proper_term(self, word: str) -> bool:
        """判断是否可能是专有名词"""
        if len(word) <= 1:
            return False
        # 含大写字母
        if any(c.isupper() for c in word):
            return True
        # 中英文混写
        if any(c.isascii() for c in word) and any(not c.isascii() for c in word):
            return True
        # 长度超过 4 的中文词
        if len(word) > 4 and all('一' <= c <= '鿿' for c in word):
            return True
        return False

    async def load_semantic_model(self):
        """加载语义排序模型（第二阶段）"""
        # 用于 RAG 检索后的候选词语义排序
        pass
