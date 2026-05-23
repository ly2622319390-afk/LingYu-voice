"""ASR 抽象接口 — 所有 ASR 引擎需实现此接口，保证可替换性"""
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional


class ASREngine(ABC):
    """ASR 引擎抽象基类"""

    @abstractmethod
    async def initialize(self):
        """初始化 ASR 引擎（加载模型、建立连接）"""
        ...

    @abstractmethod
    async def transcribe_stream(self, audio_stream) -> AsyncIterator[dict]:
        """
        流式识别，产出:
        {"type": "partial", "text": "...", "confidence": 0.95, "is_final": False}
        {"type": "final", "text": "...", "confidence": 0.98, "is_final": True}
        """
        ...

    @abstractmethod
    async def transcribe_file(self, audio_path: str) -> dict:
        """
        文件识别:
        {"text": "...", "segments": [...], "confidence": 0.96}
        """
        ...

    @abstractmethod
    async def set_hotwords(self, hotwords: list[str]):
        """
        设置热词列表（用于专业词纠错）
        热词格式: ["蓝链科技", "张翠山", "LangChain"]
        """
        ...

    @abstractmethod
    async def close(self):
        """释放资源"""
        ...


class ASREvent:
    """ASR 事件类型"""
    PARTIAL = "partial"      # 中间结果
    FINAL = "final"          # 最终结果
    ERROR = "error"          # 错误
    END = "end"              # 结束
    HOTWORD_UPDATED = "hotword_updated"
