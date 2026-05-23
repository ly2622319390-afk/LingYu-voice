"""FunASR 适配器 — 生产级中文 ASR，支持流式"""
import os
import tempfile
import logging
from typing import AsyncIterator, Optional

from pydub import AudioSegment
from .asr_interface import ASREngine, ASREvent

logger = logging.getLogger("voice-input.funasr")


class FunASRAdapter(ASREngine):
    """
    FunASR 适配器
    使用阿里巴巴 Paraformer 模型：高精度中文离线 ASR

    自动下载模型（首次约 1.5GB），支持 CPU/GPU 推理。
    """

    def __init__(self,
                 model_dir: str = "paraformer-zh",
                 device: str = "cpu",
                 hotwords: Optional[list[str]] = None):
        self.model_dir = model_dir
        self.device = device
        self._hotwords = hotwords or []
        self._model = None
        self._audio_buffer = bytearray()
        self._chunks_since_last = 0
        self._last_text = ""
        self._total_audio_ms = 0

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
        流式识别
        累积音频块，每 ~1.5s 执行一次识别并返回增量结果。
        """
        self._audio_buffer.extend(audio_chunk)
        self._chunks_since_last += 1
        self._total_audio_ms += 100  # 每块约 100ms

        # 每 15 块（约 1.5s）或积累 >2s 音频时执行一次推理
        if self._chunks_since_last >= 15 or self._total_audio_ms >= 2000:
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

            self._chunks_since_last = 0

    async def transcribe_file(self, audio_path: str) -> dict:
        """识别完整音频文件"""
        if not self._model:
            return {"text": "", "segments": [], "confidence": 0.0}

        result = self._model.generate(input=audio_path)
        text = self._extract_text(result)
        return {"text": text, "segments": [], "confidence": 0.95}

    async def transcribe_buffer(self) -> dict:
        """识别累积的音频缓冲区"""
        if not self._audio_buffer or not self._model:
            return {"text": self._last_text, "segments": [], "confidence": 0.0}

        text = await self._run_inference()
        return {"text": text or self._last_text, "segments": [], "confidence": 0.95}

    async def _run_inference(self) -> str:
        """将累积的音频缓冲区转为 WAV 并执行推理"""
        if not self._model or not self._audio_buffer:
            return ""

        tmp_webm = None
        tmp_wav = None
        try:
            # 写入临时 WebM 文件
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
                f.write(self._audio_buffer)
                tmp_webm = f.name

            # pydub + ffmpeg 转为 WAV（16kHz mono）
            segment = AudioSegment.from_file(tmp_webm, format="webm")
            segment = segment.set_frame_rate(16000).set_channels(1).set_sample_width(2)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_wav = f.name
            segment.export(tmp_wav, format="wav")

            # FunASR 推理
            kwargs = {}
            if self._hotwords:
                kwargs["hotwords"] = self._hotwords
            result = self._model.generate(input=tmp_wav, **kwargs)
            text = self._extract_text(result)

            return text.strip()

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
        self._audio_buffer.clear()


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
