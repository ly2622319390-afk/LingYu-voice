"""
情绪识别与表情推荐层

职责:
  - 情绪识别 (emotion_detector.py) — 轻量分类，不依赖大模型
  - emoji/颜文字推荐 (emoji_recommender.py) — 规则+偏好排序

设计:
  情绪标签系统 → 匹配推荐规则 → 用户偏好排序 → 最终推荐
"""
