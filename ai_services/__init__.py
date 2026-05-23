"""
AI 服务层 — 智能语音输入法

架构分层:
  ASR 层      →  ai-services/asr/     语音识别
  NLP 层      →  ai-services/nlp/     文本处理
  情绪层      →  ai-services/emotion/  情绪与表情
  词库层      →  ai-services/lexicon/  记忆与检索
  Prompt 层   →  ai-services/prompts/  模板管理
  缓存层      →  ai-services/cache/    缓存策略

设计原则:
  - 每个模块可独立替换
  - 高频轻量，低频按需
  - 大模型只做高价值任务
"""
