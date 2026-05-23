"""
NLP 文本后处理层

职责:
  - 标点恢复 (punctuation.py)
  - 专业词纠错 (correction.py)
  - 文本重写引擎 (rewrite_engine.py)

原则:
  - 不需要大模型的任务用规则+小模型
  - 标点恢复不依赖 GPT/Claude
  - 重写引擎只在办公/创作场景调用大模型
"""
