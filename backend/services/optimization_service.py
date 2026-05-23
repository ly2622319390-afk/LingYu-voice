"""场景化文本优化服务"""
import json
import random
import re


def office_polish(text: str) -> dict:
    """办公模式：生成 2-3 版润色建议"""
    # 基础的基于规则的润色（MVP 阶段，后续可接入 AI）
    formal_version = _make_formal(text)
    business_version = _make_business(text)
    concise_version = _make_concise(text)

    return {
        "origin": text,
        "versions": [
            {
                "style": "严谨版",
                "description": "适合正式报告、文档、邮件",
                "text": formal_version
            },
            {
                "style": "商务版",
                "description": "适合商务沟通、汇报、提案",
                "text": business_version
            },
            {
                "style": "简洁版",
                "description": "适合快速阅读、要点提炼",
                "text": concise_version
            }
        ]
    }


def chat_recommend(text: str) -> dict:
    """聊天模式：推荐 emoji / 颜文字"""
    emotion = _detect_emotion(text)

    # 从 emoji 库获取推荐 (通过 API 调用)
    emoji_sets = {
        "positive": [("😊", "开心友好"), ("👍", "赞同肯定"), ("✨", "精彩"), ("🎉", "祝贺")],
        "joy": [("😂", "太好笑了"), ("😄", "开心"), ("🎉", "庆祝")],
        "sad": [("😢", "有点难过"), ("💪", "加油"), ("🤗", "抱抱")],
        "thinking": [("🤔", "思考中"), ("💡", "有想法了"), ("📝", "记下来")],
        "neutral": [("😌", "好的"), ("👌", "OK"), ("🤝", "握手")],
        "frustrated": [("😤", "郁闷"), ("💪", "努力"), ("😅", "无奈")],
        "angry": [("😤", "生气"), ("💪", "冷静"), ("😮‍💨", "深呼吸")],
        "surprised": [("😮", "真的吗"), ("🤩", "太棒了"), ("😯", "惊讶")],
    }

    matched = emoji_sets.get(emotion, emoji_sets["neutral"])

    # 颜文字
    kaomoji_list = [
        "(´▽`ʃ♡ƪ)", "(｀・ω・´)", "(◕‿◕✿)",
        "(•̀ᴗ•́)و", "(∼‾▽‾)∼", "(｡ŏ_ŏ)"
    ]

    selected_kaomoji = random.sample(kaomoji_list, min(2, len(kaomoji_list)))
    selected_emoji = matched[:3]

    return {
        "origin": text,
        "emotion": emotion,
        "emoji_suggestions": [
            {"label": "轻松自然", "emojis": " ".join(e[0] for e in selected_emoji)},
            {"label": "颜文字风格", "emojis": " ".join(selected_kaomoji)}
        ],
        "all_emojis": [{"emoji": e[0], "desc": e[1]} for e in selected_emoji] +
                      [{"emoji": k, "desc": "颜文字"} for k in selected_kaomoji]
    }


def creation_process(text: str) -> dict:
    """创作模式：分段、提纲、扩写"""
    paragraphs = _auto_paragraph(text)
    outline = _generate_outline(text)
    expanded = _expand_text(text)

    return {
        "origin": text,
        "organized": {
            "style": "整理版",
            "description": "自动分段，保持原意",
            "text": "\n\n".join(paragraphs) if paragraphs else text
        },
        "outline": {
            "style": "提纲版",
            "description": "提取要点，结构化呈现",
            "text": outline
        },
        "expanded": {
            "style": "扩写版",
            "description": "丰富细节，展开表达",
            "text": expanded
        }
    }


def _make_formal(text: str) -> str:
    replacements = {
        "咱们": "我们",
        "得": "需要",
        "的事儿": "的事项",
        "搞": "执行",
        "弄": "处理",
        "想": "希望",
        "觉得": "认为",
        "好的": "同意",
        "行": "可以",
        "那个": "该",
        "啥": "什么",
        "咋": "怎么",
    }
    result = text
    for k, v in replacements.items():
        result = result.replace(k, v)
    if not result.endswith(("。", "！", "？", "。")):
        result += "。"
    return result


def _make_business(text: str) -> str:
    result = text
    business_phrases = {
        "我们": "我方",
        "需要": "需要",
        "问题": "议题",
        "做": "进行",
        "给": "提供",
        "看": "审阅",
        "说": "说明",
        "开会": "召开会议",
        "完成": "达成",
        "帮助": "协助",
        "希望": "期望",
    }
    for k, v in business_phrases.items():
        result = result.replace(k, v)
    result = "关于" + result if not result.startswith("关于") else result
    if not result.endswith(("。", "！", "？")):
        result += "。"
    return result


def _make_concise(text: str) -> str:
    sentences = re.split(r'[，。！？；,\n]', text)
    key_points = [s.strip() for s in sentences if len(s.strip()) > 4]
    if not key_points:
        key_points = [text]
    result = "\n".join(f"• {p}" for p in key_points[:5])
    return result


def _detect_emotion(text: str) -> str:
    positive_words = ["开心", "高兴", "好", "棒", "赞", "喜欢", "爱", "完美", "漂亮", "厉害", "优秀", "成功", "感谢", "谢谢", "恭喜"]
    sad_words = ["难过", "伤心", "哭", "失落", "遗憾", "可惜", "悲伤", "痛苦"]
    thinking_words = ["想", "思考", "考虑", "琢磨", "觉得", "认为", "可能", "也许", "应该", "是否", "怎么", "什么", "为什么"]
    frustrated_words = ["烦", "累", "郁闷", "崩溃", "无语", "受不了", "讨厌", "可恶", "烦死了"]
    angry_words = ["生气", "愤怒", "火大", "气死", "滚", "过分", "可恶"]
    surprised_words = ["哇", "真的", "居然", "竟然", "没想到", "天哪", "惊讶", "太"]

    text_lower = text
    pos_count = sum(1 for w in positive_words if w in text_lower)
    sad_count = sum(1 for w in sad_words if w in text_lower)
    think_count = sum(1 for w in thinking_words if w in text_lower)
    frust_count = sum(1 for w in frustrated_words if w in text_lower)
    angry_count = sum(1 for w in angry_words if w in text_lower)
    surprise_count = sum(1 for w in surprised_words if w in text_lower)

    if angry_count > 0: return "angry"
    if frust_count > 0: return "frustrated"
    if sad_count > 0: return "sad"
    if surprise_count > 0: return "surprised"
    if pos_count > 0: return "joy"
    if think_count > 2: return "thinking"

    exclamation = text.count("！") + text.count("!")
    if exclamation > 1: return "positive"

    return "neutral"


def _auto_paragraph(text: str) -> list[str]:
    sentences = re.split(r'[。！？；\n]', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) <= 2:
        return [text]
    # Group into paragraphs of 2-3 sentences
    paragraphs = []
    chunk_size = min(3, max(2, len(sentences) // 3 + 1))
    for i in range(0, len(sentences), chunk_size):
        group = sentences[i:i + chunk_size]
        paragraphs.append("。".join(group) + "。")
    return paragraphs


def _generate_outline(text: str) -> str:
    sentences = re.split(r'[。！？；\n]', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    if not sentences:
        return "（内容较短，可直接使用原文）"

    outline_parts = []
    for i, s in enumerate(sentences[:6]):
        # Extract key phrase as "title"
        words = re.findall(r'[一-鿿\w]+', s)
        if words:
            key = "、".join(words[:3]) if len(words) > 3 else s[:20]
            outline_parts.append(f"{i+1}. {key}\n   └ {s[:40]}{'…' if len(s) > 40 else ''}")

    return "\n\n".join(outline_parts) if outline_parts else text


def _expand_text(text: str) -> str:
    sentences = re.split(r'[。！？；\n]', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return text

    expanded = []
    for s in sentences[:3]:
        if len(s) < 15:
            expanded.append(f"{s}，具体来说，我们需要从多个角度来深入分析和探讨这个问题，确保全面理解和有效执行。")
        elif len(s) < 30:
            expanded.append(f"{s}，这一点的关键在于充分认识到其重要性，并在实际操作中不断优化和完善相关流程与方法。")
        else:
            expanded.append(f"{s}。在此基础上，我们还应进一步考虑可能存在的变数和风险，制定相应的应对策略和备选方案。")

    return "。".join(expanded) + "。"
