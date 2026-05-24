"""热词管理 — 用于 ASR 热词注入，提升专业词识别准确率"""
from typing import Optional


class HotwordManager:
    """
    热词管理器

    职责:
      1. 从用户词库同步高频词
      2. 从行业词库同步专业词
      3. 动态注入 ASR 引擎
      4. 管理热词优先级

    架构:
      用户词库 → HotwordManager → 排序/去重 → ASR Engine
    """

    def __init__(self, max_hotwords: int = 100):
        self.max_hotwords = max_hotwords
        self._hotwords: dict[str, int] = {}  # word -> priority

    def sync_from_lexicon(self, words: list[dict]):
        """
        从词库同步热词
        word: {"word": "LangChain", "usage_count": 10, "word_type": "...", "confidence": 0.9}
        """
        for w in words:
            priority = (w.get("usage_count", 0) * 10) + int(w.get("confidence", 0) * 100)
            self._hotwords[w["word"]] = priority

    def sync_from_industry(self, words: list[dict]):
        """从行业词库同步热词"""
        for w in words:
            priority = int(w.get("confidence", 0.9) * 100)
            self._hotwords[w["word"]] = priority

    def add_hotword(self, word: str, priority: int = 50):
        self._hotwords[word] = max(self._hotwords.get(word, 0), priority)

    def get_top_hotwords(self, limit: Optional[int] = None) -> list[str]:
        limit = limit or self.max_hotwords
        sorted_words = sorted(self._hotwords.items(), key=lambda x: -x[1])
        return [w for w, _ in sorted_words[:limit]]

    def sync_from_industry_system(self, industry_system_hotwords: list[str]):
        """从行业词库系统同步热词"""
        for word in industry_system_hotwords:
            self._hotwords[word] = max(self._hotwords.get(word, 0), 80)  # 行业词给予较高优先级

    def rebuild_from_sources(self, user_words: list[dict], industry_hotwords: list[str]):
        """从全部来源重建热词表"""
        self._hotwords.clear()
        # 用户词库（最高优先级）
        for w in user_words:
            priority = (w.get("usage_count", 0) * 10) + int(w.get("confidence", 0) * 100)
            self._hotwords[w["word"]] = priority
        # 行业词（次高优先级）
        for word in industry_hotwords:
            self._hotwords[word] = max(self._hotwords.get(word, 0), 80)

    def clear(self):
        self._hotwords.clear()
