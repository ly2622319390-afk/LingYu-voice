"""
情绪识别模块 — AI 架构第 5 项

当前: 基于关键词+规则的轻量分类器
后续: 接入小模型 (BERT small / MiniCPM) 做更精细的情绪分析

输出格式:
  {
    "primary_emotion": "happy",
    "scores": {"happy": 0.91, "excited": 0.88, ...},
    "intensity": "high"
  }
"""

import re

# 情绪标签体系（AI 架构要求）
EMOTION_LABELS = [
    "happy", "excited", "angry", "sad", "cute",
    "shy", "sarcastic", "relaxed", "neutral", "surprised",
    "frustrated", "loving", "grateful", "worried"
]

# 情绪关键词映射
EMOTION_KEYWORDS = {
    "happy": ["开心", "高兴", "快乐", "哈哈", "嘻嘻", "耶", "爽", "棒", "太棒了"],
    "excited": ["激动", "兴奋", "太期待", "太开心", "受不了了", "疯狂", "超级"],
    "angry": ["生气", "愤怒", "气人", "火大", "气死", "可恶", "有病", "过分"],
    "sad": ["难过", "伤心", "哭", "失落", "可惜", "悲伤", "心累", "难受", "惨"],
    "cute": ["可爱", "萌", "乖", "好乖", "萌萌", "小可"],
    "shy": ["害羞", "不好意思", "尴尬", "有点那个", "羞"],
    "sarcastic": ["呵呵", "哦是吗", "真行", "真棒", "厉害了啊"],
    "relaxed": ["轻松", "舒服", "惬意", "悠闲", "自在", "随意"],
    "surprised": ["哇", "真的吗", "居然", "竟然", "没想到", "天哪", "惊讶", "太"],
    "frustrated": ["烦", "累", "郁闷", "崩溃", "无语", "受不了", "讨厌", "心累"],
    "loving": ["爱", "喜欢", "好喜欢", "超爱", "爱你", "亲爱的"],
    "grateful": ["感谢", "谢谢", "感恩", "感激", "多谢", "辛苦了"],
    "worried": ["担心", "焦虑", "怕", "不安", "紧张", "慌"]
}


class EmotionDetector:
    """
    情绪识别器

    基于关键词匹配的分值计算，输出多维情绪向量。
    符合 AI 架构第 5.2 节输出格式要求。
    """

    def __init__(self):
        self._model = None  # 预留小模型

    def detect(self, text: str) -> dict:
        """
        分析文本情绪

        Returns:
            primary_emotion: str  主导情绪
            scores: dict[str, float]  各情绪分值 (0~1)
            intensity: str  "high" | "medium" | "low"
        """
        if not text:
            return {"primary_emotion": "neutral", "scores": {"neutral": 1.0}, "intensity": "low"}

        scores = {}
        for emotion, keywords in EMOTION_KEYWORDS.items():
            score = 0
            for kw in keywords:
                count = text.count(kw)
                if count > 0:
                    score += count * 0.3
                    # 相邻词加分（如 "非常开心"）
                    if kw in text:
                        score += 0.1
            if score > 0:
                scores[emotion] = min(score, 1.0)

        # 中性情绪保底
        if not scores:
            scores["neutral"] = 0.8
        elif max(scores.values()) < 0.3:
            scores["neutral"] = max(scores.get("neutral", 0), 0.5)

        # 归一化
        max_score = max(scores.values()) if scores else 1
        if max_score > 1:
            scores = {k: v / max_score for k, v in scores.items()}

        # 主导情绪
        primary = max(scores, key=scores.get) if scores else "neutral"
        max_val = scores.get(primary, 0)

        intensity = "high" if max_val >= 0.7 else "medium" if max_val >= 0.4 else "low"

        return {
            "primary_emotion": primary,
            "scores": dict(sorted(scores.items(), key=lambda x: -x[1])),
            "intensity": intensity
        }

    async def load_model(self):
        """加载小模型（第二阶段）"""
        # from transformers import pipeline
        # self._model = pipeline("text-classification", model="bert-base-chinese-emotion")
        pass
