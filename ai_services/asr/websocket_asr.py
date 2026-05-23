"""WebSocket 实时语音识别链路 — AI 架构第 8 项要求"""
from typing import Optional
import json


class ASRWebSocketHandler:
    """
    WebSocket ASR 处理器

    架构:
      前端麦克风 → WebSocket → 后端 ASR 流式识别 → WebSocket → 前端展示

    消息格式:
      客户端 → 服务端: {"type": "audio", "data": "<base64_audio_chunk>"}
      服务端 → 客户端: {"type": "partial", "text": "...", "confidence": 0.9}
      服务端 → 客户端: {"type": "final", "text": "...", "confidence": 0.95}

    在 FastAPI 中使用:
      @app.websocket("/ws/asr")
      async def asr_websocket(websocket: WebSocket):
          handler = ASRWebSocketHandler(asr_engine)
          await handler.handle(websocket)
    """

    def __init__(self, asr_engine):
        self.asr_engine = asr_engine
        self._hotwords: list[str] = []

    async def handle(self, websocket):
        await websocket.accept()
        await self.asr_engine.initialize()

        try:
            while True:
                message = await websocket.receive_text()
                data = json.loads(message)
                msg_type = data.get("type", "")

                if msg_type == "audio":
                    await self._process_audio(websocket, data.get("data", ""))
                elif msg_type == "set_hotwords":
                    self._hotwords = data.get("hotwords", [])
                    await self.asr_engine.set_hotwords(self._hotwords)
                    await websocket.send_json({"type": "hotword_updated", "hotwords": self._hotwords})
                elif msg_type == "stop":
                    await websocket.send_json({"type": "end"})
                    break
                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

        except Exception as e:
            await websocket.send_json({"type": "error", "message": str(e)})
        finally:
            await self.asr_engine.close()

    async def _process_audio(self, websocket, audio_data: str):
        """处理音频数据块，返回识别结果"""
        # 实际调用 ASR 引擎的流式识别
        async for result in self.asr_engine.transcribe_stream(audio_data):
            await websocket.send_json(result)

    @property
    def hotwords(self) -> list[str]:
        return self._hotwords
