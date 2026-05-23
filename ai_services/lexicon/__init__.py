"""
词库与用户记忆层

职责:
  - RAG 词库检索 (lexicon_rag.py)
  - 用户画像与学习 (user_profile.py)

架构:
  ASR输出 → 词库召回 → RAG检索 → 语义排序 → 候选词
"""
