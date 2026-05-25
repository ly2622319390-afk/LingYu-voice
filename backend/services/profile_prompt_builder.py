"""
用户偏好提示构建器

从 profiles_db 和 edit_log_db 读取用户历史偏好，
构建自然语言上下文块，注入 LLM system prompt。
"""

import logging
from typing import Optional

logger = logging.getLogger("voice-input.profile_prompt")


def build_preference_context(user_id: str = "default") -> str:
    """
    构建用户偏好上下文块，供 LLM 使用。

    返回格式:

    ## 用户偏好参考（基于历史编辑学习）
    ### 风格偏好
    - formality: formal (置信度: 3.0)
    - conciseness: concise (置信度: 2.0)

    ### 使用场景
    - 办公: 15 次
    - 聊天: 8 次

    ### ASR 高频修正
    - 「framework」→「Framework」(3 次)
    - 「克劳德」→「Claude」(2 次)
    """
    if not _has_database():
        return ""

    parts = []

    # 1. 风格偏好
    preferences = _get_preferences(user_id)
    if preferences:
        pref_lines = ["\n### 风格偏好"]
        for pref in preferences[:5]:
            key = pref.get("pref_key", "")
            val = pref.get("pref_value", "")
            conf = pref.get("confidence", 1.0)
            pref_lines.append(f"- {key}: {val} (置信度: {conf})")
        parts.append("\n".join(pref_lines))

    # 2. 场景使用
    scene_usage = _get_scene_usage(user_id)
    if scene_usage:
        scene_lines = ["\n### 使用场景"]
        for s in scene_usage[:5]:
            scene_lines.append(f"- {s.get('scene_type', '')}: {s.get('usage_count', 0)} 次")
        parts.append("\n".join(scene_lines))

    # 3. ASR 高频修正
    asr_fixes = _get_asr_fixes(user_id)
    if asr_fixes:
        fix_lines = ["\n### ASR 高频修正"]
        for fix in asr_fixes[:5]:
            fix_lines.append(f"- 「{fix.get('original_word', '')}」→「{fix.get('edited_word', '')}」({fix.get('count', 0)} 次)")
        parts.append("\n".join(fix_lines))

    if not parts:
        return ""

    header = "## 用户偏好参考（基于历史编辑学习）"
    return header + "\n" + "\n".join(parts)


def build_full_context(user_id: str = "default") -> str:
    """构建完整的上下文信息（偏好 + 热词 + 活跃行业）"""
    parts = []

    # 偏好上下文
    pref = build_preference_context(user_id)
    if pref:
        parts.append(pref)

    # 热词上下文
    hotwords = _get_hotwords()
    if hotwords:
        parts.append("\n## 当前活跃热词\n" + ", ".join(hotwords[:20]))

    return "\n\n".join(parts)


def _has_database() -> bool:
    try:
        from database import profiles_db
        return True
    except ImportError:
        return False


def _get_preferences(user_id: str) -> list:
    try:
        from database import profiles_db
        return profiles_db.get_top_preferences(user_id, top_k=10)
    except Exception as e:
        logger.debug(f"获取偏好失败: {e}")
        return []


def _get_scene_usage(user_id: str) -> list:
    try:
        from database import profiles_db
        return profiles_db.get_scene_usage(user_id)
    except Exception as e:
        logger.debug(f"获取场景统计失败: {e}")
        return []


def _get_asr_fixes(user_id: str) -> list[dict]:
    """从 edit_log 聚合高频 ASR 修正对"""
    try:
        from database import edit_log_db
        logs = edit_log_db.get_recent_asr_fixes(user_id, limit=100)
    except Exception:
        return []

    # 统计修正对频次
    fix_pairs = {}
    for log in logs:
        ops = log.get("diff_operations", [])
        if not ops:
            continue
        for op in ops:
            if op.get("classification") == "asr_fix":
                ow = op.get("original_word", "")
                ew = op.get("edited_word", "")
                if ow and ew:
                    key = f"{ow}|{ew}"
                    fix_pairs[key] = fix_pairs.get(key, 0) + 1

    return [
        {"original_word": k.split("|")[0], "edited_word": k.split("|")[1], "count": v}
        for k, v in sorted(fix_pairs.items(), key=lambda x: -x[1])
    ]


def _get_hotwords() -> list:
    try:
        from main import hotword_manager
        return hotword_manager.get_top_hotwords(20)
    except Exception:
        return []
