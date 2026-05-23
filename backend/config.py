"""全局配置 — AI 架构参数"""

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 项目
    APP_NAME: str = "智能语音输入法"
    VERSION: str = "2.0.0"
    DEBUG: bool = True

    # 后端
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 数据库目录
    DATABASES_DIR: str = "databases"

    # AI 服务
    ASR_ENGINE: str = "funasr"  # webspeech | funasr | whisper
    ASR_DEVICE: str = "cpu"
    ASR_AUDIO_INPUT: str = "http"   # http | websocket | file

    # 桌面模式
    DESKTOP_MODE: bool = False      # Electron 桌面端启用
    ASR_WS_ENABLED: bool = True     # 启用 WebSocket ASR 端点

    # 大模型 (Anthropic)
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-sonnet-20241022"
    LLM_ENABLED: bool = False

    # 大模型 (OpenAI)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # 缓存
    CACHE_ENABLED: bool = True
    CACHE_TTL_EMOTION: int = 300
    CACHE_TTL_OPTIMIZE: int = 3600

    # 热词
    MAX_HOTWORDS: int = 100

    # 标点
    PUNCTUATION_MODEL: str = "rule"

    # MVP 模式
    MVP_MODE: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
