"""
ASR 语音识别层

职责:
  - 实时语音转文字
  - 流式识别
  - 中英混输
  - 热词注入
  - 断句

抽象接口 asr_interface.py 定义统一契约，
具体实现由 funasr_adapter.py (FunASR) 或 whisper_adapter.py (Whisper) 提供。
"""
