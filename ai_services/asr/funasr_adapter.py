"""FunASR 适配器 — 生产级中文 ASR，支持流式"""
import os
import subprocess
import tempfile
import logging
from typing import AsyncIterator, Optional

from .asr_interface import ASREngine, ASREvent

logger = logging.getLogger("voice-input.funasr")

# 每批处理的音频块数（每块 ~100ms，10块 = ~1s）
# 该值越小延迟越低，但太小编码 overhead 占比高
BATCH_SIZE = 10


class FunASRAdapter(ASREngine):
    """
    FunASR 适配器
    使用阿里巴巴 Paraformer 模型：高精度中文离线 ASR

    采用滑动窗口策略：首个 block（含 EBML header）单独保存，
    每次推理只处理 header + 最近 ~1.5s 的音频块，避免累积整个会话的音频。

    每次推理后清空 pending 块，保证响应速度恒定。
    """

    def __init__(self,
                 model_dir: str = "paraformer-zh",
                 device: str = "cpu",
                 hotwords: Optional[list[str]] = None):
        self.model_dir = model_dir
        self.device = device
        self._hotwords = hotwords or []
        self._model = None
        # 滑动窗口状态
        self._header_chunk: Optional[bytes] = None  # 首个 block（含 EBML header）
        self._pending_chunks: list[bytes] = []       # 自上次推理以来的新 block
        self._chunks_since_last = 0
        self._last_text = ""

    async def initialize(self):
        """初始化 FunASR 模型（自动从 ModelScope 下载）"""
        logger.info(f"正在加载 FunASR 模型: {self.model_dir} (device={self.device})")
        logger.info("首次加载会自动下载模型（约 1.5GB），请耐心等待...")

        from funasr import AutoModel
        self._model = AutoModel(
            model=self.model_dir,
            vad_model="fsmn-vad",
            punc_model="ct-punc",
            device=self.device,
            disable_update=True,
        )
        logger.info("FunASR 模型加载成功")

    async def transcribe_stream(self, audio_chunk: bytes) -> AsyncIterator[dict]:
        """
        流式识别 — 滑动窗口模式

        保存首个 block 作为 header，后续 block 累积到 pending 列表。
        每 BATCH_SIZE 块（~1s）构建 header+pending 进行推理，结束后清空 pending。
        每次推理数据量恒定，响应速度不随录音时长增加而下降。
        """
        # 首个到达的 block 保存为 header（含 EBML header）
        if self._header_chunk is None:
            self._header_chunk = audio_chunk

        self._pending_chunks.append(audio_chunk)
        self._chunks_since_last += 1

        # 每 BATCH_SIZE 块执行一次推理
        if self._chunks_since_last >= BATCH_SIZE:
            text = await self._run_inference()

            if text and text != self._last_text:
                # 只返回增量部分
                new_part = text[len(self._last_text):] if text.startswith(self._last_text) else text
                if new_part.strip():
                    yield {
                        "type": ASREvent.PARTIAL,
                        "text": text,
                        "confidence": 0.92,
                    }
                self._last_text = text

            # 清空 pending（保留 header 供下一轮使用）
            self._pending_chunks.clear()
            self._chunks_since_last = 0

    async def transcribe_file(self, audio_path: str) -> dict:
        """识别完整音频文件"""
        if not self._model:
            return {"text": "", "segments": [], "confidence": 0.0}

        result = self._model.generate(input=audio_path)
        text = self._extract_text(result)
        return {"text": text, "segments": [], "confidence": 0.95}

    async def transcribe_buffer(self) -> dict:
        """
        识别累积的音频缓冲区并 **清空所有状态**，使下次录音可以重新开始。

        在用户停止录音时由后端调用，返回最终完整文本。
        """
        if not self._pending_chunks or not self._model:
            text = self._last_text
            self._reset_state()
            return {"text": text, "segments": [], "confidence": 0.0}

        text = await self._run_inference()
        result_text = text or self._last_text
        self._reset_state()
        return {"text": result_text, "segments": [], "confidence": 0.95}

    def _reset_state(self):
        """重置滑动窗口状态，使下次录音从零开始"""
        self._header_chunk = None
        self._pending_chunks.clear()
        self._chunks_since_last = 0
        self._last_text = ""

    async def _run_inference(self) -> str:
        """
        将 header + pending 块转为 WAV 并执行推理。
        每次处理约 BATCH_SIZE * 100ms 音频，保证响应速度恒定。
        """
        if not self._model or not self._pending_chunks:
            return ""

        tmp_webm = None
        tmp_wav = None
        try:
            # 写入临时 WebM 文件（header + 最新一批 block）
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
                if self._header_chunk:
                    f.write(self._header_chunk)
                for chunk in self._pending_chunks:
                    f.write(chunk)
                tmp_webm = f.name

            # 直接 ffmpeg 转 WAV（避免 pydub 的额外 import/overhead）
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_wav = f.name
            subprocess.run(
                ["ffmpeg", "-y", "-i", tmp_webm,
                 "-ar", "16000", "-ac", "1", "-sample_fmt", "s16",
                 tmp_wav],
                capture_output=True, check=True, timeout=10,
            )

            # FunASR 推理
            kwargs = {}
            if self._hotwords:
                kwargs["hotwords"] = self._hotwords
            result = self._model.generate(input=tmp_wav, **kwargs)
            text = self._extract_text(result)

            return text.strip()

        except subprocess.TimeoutExpired:
            logger.warning("ffmpeg 转码超时")
            return ""
        except Exception as e:
            logger.warning(f"FunASR 推理异常: {e}")
            return ""
        finally:
            for p in [tmp_webm, tmp_wav]:
                if p and os.path.exists(p):
                    try:
                        os.unlink(p)
                    except OSError:
                        pass

    async def set_hotwords(self, hotwords: list[str]):
        """设置热词（FunASR 1.3.x 通过 generate(hotwords=...) 传入）"""
        self._hotwords = hotwords

    @staticmethod
    def _extract_text(result) -> str:
        """从 FunASR 1.3.x 返回结果中提取文本"""
        if isinstance(result, list):
            parts = []
            for r in result:
                if isinstance(r, dict):
                    parts.append(r.get("text", ""))
                else:
                    parts.append(str(r))
            return "".join(parts).strip()
        elif isinstance(result, dict):
            return result.get("text", "").strip()
        return str(result).strip()

    async def close(self):
        self._model = None
        self._reset_state()


class WhisperAdapter(ASREngine):
    """Whisper 适配器 — 多语言强，适合海外版本（当前为占位）"""

    def __init__(self, model_size: str = "medium", device: str = "cpu"):
        self.model_size = model_size
        self.device = device
        self._model = None

    async def initialize(self):
        """安装: pip install openai-whisper"""
        # import whisper
        # self._model = whisper.load_model(self.model_size, device=self.device)
        pass

    async def transcribe_stream(self, audio_stream) -> AsyncIterator[dict]:
        yield {"type": ASREvent.FINAL, "text": "[Whisper 待接入]", "confidence": 0.0}

    async def transcribe_file(self, audio_path: str) -> dict:
        return {"text": "[Whisper 待接入]", "segments": [], "confidence": 0.0}

    async def set_hotwords(self, hotwords: list[str]):
        pass

    async def close(self):
        self._model = None


class WebSpeechASR(ASREngine):
    """
    浏览器 Web Speech API 适配器
    MVP 阶段使用，无需部署，前端直接调用浏览器能力
    """

    def __init__(self):
        self._hotwords: list[str] = []

    async def initialize(self):
        pass

    async def transcribe_stream(self, audio_stream) -> AsyncIterator[dict]:
        yield {"type": ASREvent.FINAL, "text": "[前端 Web Speech API]", "confidence": 0.0}

    async def transcribe_file(self, audio_path: str) -> dict:
        return {"text": "[前端 Web Speech API]", "segments": [], "confidence": 0.0}

    async def set_hotwords(self, hotwords: list[str]):
        self._hotwords = hotwords

    async def close(self):
        pass
