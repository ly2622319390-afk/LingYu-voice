"""
用户画像与学习系统 — AI 架构第 9 项 "用户记忆学习"

记录:
  - 常用词 / 修正词 / emoji偏好 / 标点习惯 / 风格偏好 / 场景偏好

架构:
  用户行为 → 特征提取 → 持久化 → 影响推荐排序
"""


class UserProfile:
    """
    用户画像

    记录用户的使用习惯，为推荐提供个性化信号。
    数据存储在独立的 profiles.db 中。
    """

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.stats = {
            "total_sessions": 0,
            "total_recordings": 0,
            "total_corrections": 0,
            "total_optimizations": 0,
            "emoji_usage": {},  # emoji -> count
            "scene_usage": {},  # scene -> count
            "style_preference": {},  # style -> count
            "common_words": {},  # word -> count
            "punctuation_style": {}  # punctuation -> count
        }

    def record_session(self):
        self.stats["total_sessions"] += 1

    def record_correction(self, original: str, corrected: str):
        self.stats["total_corrections"] += 1
        self.stats["common_words"][corrected] = self.stats["common_words"].get(corrected, 0) + 1

    def record_emoji_usage(self, emoji: str):
        self.stats["emoji_usage"][emoji] = self.stats["emoji_usage"].get(emoji, 0) + 1

    def record_scene_usage(self, scene: str):
        self.stats["scene_usage"][scene] = self.stats["scene_usage"].get(scene, 0) + 1

    def record_style(self, style: str):
        self.stats["style_preference"][style] = self.stats["style_preference"].get(style, 0) + 1

    def to_dict(self) -> dict:
        return {"user_id": self.user_id, "stats": self.stats}

    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        profile = cls(data.get("user_id", "default"))
        profile.stats.update(data.get("stats", {}))
        return profile
