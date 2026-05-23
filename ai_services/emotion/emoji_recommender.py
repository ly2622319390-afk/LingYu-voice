"""
Emoji / 颜文字推荐模块 — AI 架构第 6 项

架构:
  情绪分析 → emoji候选池 → 场景过滤 → 用户风格过滤 → 最终推荐

原则:
  - 不调大模型实时生成
  - 预构建 emoji 情绪映射库
  - 用户偏好排序
"""

import random
from typing import Optional


class EmojiRecommender:
    """
    Emoji 推荐器

    Usage:
        recommender = EmojiRecommender()
        result = recommender.recommend("今天好开心啊", scene="聊天")
        # {"emotion": "happy", "emoji_suggestions": [...], "all_emojis": [...]}
    """

    def __init__(self):
        self._user_preferences: dict[str, int] = {}

    def recommend(self, text: str, scene: str = "聊天",
                  emotion_result: Optional[dict] = None,
                  emoji_db: Optional[list[dict]] = None) -> dict:
        if not emotion_result:
            from .emotion_detector import EmotionDetector
            emotion_result = EmotionDetector().detect(text)

        primary = emotion_result["primary_emotion"]
        candidates = self._get_candidates(primary, scene, emoji_db)

        candidates.sort(key=lambda e: (
            self._user_preferences.get(e.get("emoji", ""), 0),
            e.get("usage_priority", 0)
        ), reverse=True)

        emoji_only = [e for e in candidates if len(e.get("emoji", "")) <= 2]
        kaomoji_only = [e for e in candidates if len(e.get("emoji", "")) > 2]

        return {
            "origin": text,
            "emotion": primary,
            "emoji_suggestions": [
                {"label": "轻松自然", "emojis": " ".join(e["emoji"] for e in emoji_only[:3])},
                {"label": "颜文字风格", "emojis": " ".join(e["emoji"] for e in kaomoji_only[:2])}
            ],
            "all_emojis": [
                {"emoji": e["emoji"], "desc": e.get("emotion_tags", "")}
                for e in (emoji_only[:4] + kaomoji_only[:2])
            ]
        }

    def _get_candidates(self, emotion: str, scene: str,
                        emoji_db: Optional[list[dict]]) -> list[dict]:
        if emoji_db:
            matched = []
            for e in emoji_db:
                tags = e.get("emotion_tags", "")
                scenes = e.get("scene_tags", "")
                if emotion in tags and scene in scenes:
                    matched.append(e)
            if matched:
                return matched
            return [e for e in emoji_db if scene in e.get("scene_tags", "")]

        defaults = {
            "happy": [{"emoji": "😊", "emotion_tags": "开心", "usage_priority": 90},
                      {"emoji": "😄", "emotion_tags": "开心", "usage_priority": 85}],
            "excited": [{"emoji": "🎉", "emotion_tags": "激动", "usage_priority": 95},
                        {"emoji": "🔥", "emotion_tags": "热情", "usage_priority": 85}],
            "sad": [{"emoji": "😢", "emotion_tags": "难过", "usage_priority": 80},
                    {"emoji": "💪", "emotion_tags": "鼓励", "usage_priority": 75}],
            "loving": [{"emoji": "🥰", "emotion_tags": "爱", "usage_priority": 90}],
            "neutral": [{"emoji": "😌", "emotion_tags": "平静", "usage_priority": 80},
                        {"emoji": "👍", "emotion_tags": "好", "usage_priority": 85}],
        }
        matched = defaults.get(emotion, defaults["neutral"])[:4]

        kaomoji_pool = [
            {"emoji": "(´▽`ʃ♡ƪ)", "emotion_tags": "开心", "usage_priority": 70},
            {"emoji": "(｡ŏ_ŏ)", "emotion_tags": "疑惑", "usage_priority": 65},
            {"emoji": "¯\\_(ツ)_/¯", "emotion_tags": "无奈", "usage_priority": 60},
        ]
        random.shuffle(kaomoji_pool)
        return matched + kaomoji_pool[:2]

    def record_usage(self, emoji: str):
        self._user_preferences[emoji] = self._user_preferences.get(emoji, 0) + 1
