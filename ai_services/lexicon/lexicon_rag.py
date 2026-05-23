"""
词库 RAG 检索 — AI 架构第 3 项 "RAG检索"

当前: 基于 SQL LIKE 的简单检索
后续: 接入 embedding 检索 (sentence-transformers)

架构:
  ASR 输出段落 → 提取候选术语 → embedding 向量化 → 词库向量检索 → 语义排序
"""

import re
from typing import Optional


class LexiconRAG:
    """
    词库 RAG 检索器

    Usage:
        rag = LexiconRAG()
        candidates = rag.retrieve("今天我们讨论langchain和rag架构")
        # [{"word": "LangChain", "score": 0.95, "source": "user"}, ...]
    """

    def __init__(self):
        self._embedding_model = None  # 预留 embedding 模型
        self._user_vectors: list[dict] = []
        self._industry_vectors: list[dict] = []

    def retrieve(self, text: str,
                 user_lexicon: list[dict],
                 industry_lexicon: list[dict] = None) -> list[dict]:
        """
        从词库中检索匹配的候选词

        当前: 基于模糊匹配 + 拼音近似
        后续: embedding 向量相似度检索
        """
        candidates = []

        # 提取文本中的候选词组
        words = self._extract_candidates(text)

        for word in words:
            # 用户词库匹配
            for entry in (user_lexicon or []):
                score = self._match_score(word, entry["word"])
                if score > 0.6:
                    candidates.append({
                        "word": entry["word"],
                        "original": word,
                        "score": score,
                        "source": "user",
                        "type": entry.get("word_type", ""),
                        "confidence": entry.get("confidence", 0.8)
                    })

            # 行业词库匹配
            for entry in (industry_lexicon or []):
                score = self._match_score(word, entry["word"])
                if score > 0.6:
                    candidates.append({
                        "word": entry["word"],
                        "original": word,
                        "score": score,
                        "source": "industry",
                        "type": entry.get("word_type", ""),
                        "confidence": entry.get("confidence", 0.9)
                    })

        # 去重排序
        seen = set()
        unique = []
        for c in sorted(candidates, key=lambda x: -x["score"]):
            key = c["word"]
            if key not in seen:
                seen.add(key)
                unique.append(c)

        return unique

    def _extract_candidates(self, text: str) -> list[str]:
        """从文本提取候选词组"""
        words = re.findall(r'[一-鿿\w]+', text)
        # 对英文词组保持原样，中文词按字组合
        result = []
        for w in words:
            if len(w) >= 2:
                result.append(w)
        return result

    def _match_score(self, query: str, term: str) -> float:
        """
        计算查询词与词库词条的匹配度
        后续升级为 embedding 余弦相似度
        """
        q = query.lower().strip()
        t = term.lower().strip()

        if q == t:
            return 1.0
        if t.startswith(q) or q.startswith(t):
            return 0.85
        if t in q or q in t:
            return 0.7
        # 拼音近似（第二阶段）
        return 0.0

    async def load_embedding_model(self):
        """加载 embedding 模型（第二阶段）"""
        # from sentence_transformers import SentenceTransformer
        # self._embedding_model = SentenceTransformer('BAAI/bge-small-zh-v1.5')
        pass
