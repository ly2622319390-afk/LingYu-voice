"""
编辑分析引擎 — 编辑追踪与学习系统的核心智能

职责:
  1. compute_word_diff()    — 词级别 diff（jieba 分词 + difflib）
  2. classify_edit()        — 分类每处改动（asr_fix / style_change / content_add / content_delete / punctuation）
  3. analyze_edits()        — 全流程编排：diff → 分类 → 执行学习动作 → 返回结果
"""

import difflib
import logging
from typing import Optional

import jieba

logger = logging.getLogger("voice-input.edit_analyzer")

# ─── 口语→书面 映射表（可扩展） ───
ORAL_TO_WRITTEN = {
    "咱们": "我们",
    "大伙": "大家",
    "的事儿": "的事情",
    "啥": "什么",
    "咋": "怎么",
    "甭": "不用",
    "挺": "很",
    "特": "特别",
    "超": "非常",
    "贼": "很",
    "老": "很",
    "好滴": "好的",
    "ok": "好的",
    "嗯呢": "嗯",
    "行吧": "好的",
    "中": "可以",
    "管": "可以",
}


def compute_word_diff(original: str, edited: str) -> list[dict]:
    """
    词级别 diff，返回操作列表。

    每项:
      {
        "type": "equal" | "replace" | "insert" | "delete",
        "original_word": str,   # 原文中的词（replace/delete/equal 时有值）
        "edited_word": str,     # 编辑后的词（replace/insert/equal 时有值）
        "position": int         # 在原文中的位置（词索引）
      }
    """
    if original == edited:
        return []

    orig_tokens = list(jieba.cut(original))
    edit_tokens = list(jieba.cut(edited))

    matcher = difflib.SequenceMatcher(None, orig_tokens, edit_tokens)
    ops = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for idx in range(i1, i2):
                ops.append({
                    "type": "equal",
                    "original_word": orig_tokens[idx],
                    "edited_word": orig_tokens[idx],
                    "position": idx,
                })
        elif tag == "replace":
            # 将 replace 按词展开，逐词对比
            for idx in range(max(i2 - i1, j2 - j1)):
                ow = orig_tokens[i1 + idx] if i1 + idx < i2 else ""
                ew = edit_tokens[j1 + idx] if j1 + idx < j2 else ""
                if ow and ew:
                    ops.append({
                        "type": "replace",
                        "original_word": ow,
                        "edited_word": ew,
                        "position": i1 + idx,
                    })
                elif ew:
                    ops.append({
                        "type": "insert",
                        "original_word": "",
                        "edited_word": ew,
                        "position": i1 + idx,
                    })
                elif ow:
                    ops.append({
                        "type": "delete",
                        "original_word": ow,
                        "edited_word": "",
                        "position": i1 + idx,
                    })
        elif tag == "delete":
            for idx in range(i1, i2):
                ops.append({
                    "type": "delete",
                    "original_word": orig_tokens[idx],
                    "edited_word": "",
                    "position": idx,
                })
        elif tag == "insert":
            for idx in range(j1, j2):
                ops.append({
                    "type": "insert",
                    "original_word": "",
                    "edited_word": edit_tokens[idx],
                    "position": i1,  # 插入位置标记在原文当前位置
                })

    # 过滤掉 equal（前端不需要）
    return [op for op in ops if op["type"] != "equal"]


def _is_punctuation_only(word: str) -> bool:
    """判断是否纯标点符号"""
    if not word:
        return False
    import re
    return bool(re.match(r'^[，。！？、；：""''（）【】《》\-+\s.,!?;:\"\'()\[\]{}]+$', word))


def _pinyin_similar(word1: str, word2: str) -> float:
    """计算两个词的拼音相似度（0~1），用 pypinyin 取全拼对比"""
    try:
        from pypinyin import pinyin, Style
        p1 = "".join(item[0] for item in pinyin(word1, style=Style.NORMAL))
        p2 = "".join(item[0] for item in pinyin(word2, style=Style.NORMAL))
        if not p1 or not p2:
            return 0.0
        # 编辑距离归一化
        ratio = difflib.SequenceMatcher(None, p1, p2).ratio()
        return ratio
    except ImportError:
        logger.warning("pypinyin 未安装，拼音相似度检测不可用")
        return 0.0
    except Exception:
        return 0.0


def _is_oral_to_written(original_word: str, edited_word: str) -> bool:
    """检测是否口语→书面转换"""
    return ORAL_TO_WRITTEN.get(original_word) == edited_word


def _is_in_lexicon(word: str) -> bool:
    """检查词是否在任何词库中"""
    try:
        from database import lexicon_db
        result = lexicon_db.check_known_word("default", word)
        if result:
            return True
    except Exception:
        pass

    try:
        from database import industry_lexicon_db
        industries = industry_lexicon_db.get_all_industries()
        for industry in industries:
            words = industry_lexicon_db.get_industry_words(industry.get("name", ""))
            if words and any(w.get("word") == word for w in words):
                return True
    except Exception:
        pass

    return False


def classify_edit(change: dict, scene: str = "",
                  user_history: Optional[list] = None) -> str:
    """
    对单处改动进行分类。

    分类优先级:
      1. punctuation         — 纯标点变化
      2. asr_fix             — 同音词 / 词库中存在
      3. style_change        — 口语→书面映射
      4. content_delete      — 原文有，编辑后无
      5. content_add         — 原文无，编辑后有
    """
    ow = change.get("original_word", "")
    ew = change.get("edited_word", "")
    op_type = change.get("type", "")

    # 标点变化
    if _is_punctuation_only(ow) or _is_punctuation_only(ew):
        return "punctuation"

    if op_type == "replace":
        # ASR 修正：同音词 或 编辑后的词在词库中
        pinyin_score = _pinyin_similar(ow, ew)
        if pinyin_score > 0.6 or _is_in_lexicon(ew):
            return "asr_fix"

        # 口语→书面
        if _is_oral_to_written(ow, ew):
            return "style_change"

        # 检查正式度变化（长度差异大 = style change）
        if abs(len(ew) - len(ow)) > 2:
            return "style_change"

        # 默认归为内容调整
        return "style_change"

    elif op_type == "delete":
        # 删除语气词 / 冗余词
        filler_words = {"嗯", "呃", "啊", "那个", "这个", "就是", "然后", "反正", "其实",
                        "感觉", "就是", "可以说", "那么", "所以说", "我觉得", "我认为"}
        if ow in filler_words:
            return "style_change"
        return "content_delete"

    elif op_type == "insert":
        return "content_add"

    return "style_change"


def _learn_from_asr_fix(user_id: str, original_word: str, edited_word: str):
    """从 ASR 修正中学习：更新热词 + 词库 + misrecognition_map"""
    try:
        from backend.database import corrections_db
        from backend.database import lexicon_db
        from main import hotword_manager
    except ImportError:
        from database import corrections_db
        from database import lexicon_db
        # 无法导入 hotword_manager (运行时在 main 中持有)
        # 返回数据让调用方处理
        pass

    try:
        # 记录到修正日志
        corrections_db.log_correction(
            user_id, original_word, edited_word,
            "asr_fix", "", ""
        )
    except Exception as e:
        logger.debug(f"记录修正日志失败: {e}")

    try:
        # 自动加入用户词库
        lexicon_db.add_word(user_id, edited_word, word_type="AI修正", source="编辑分析")
    except Exception as e:
        logger.debug(f"加入词库失败: {e}")

    return {
        "learned": True,
        "action": "added_to_lexicon",
        "word": edited_word
    }


def _learn_from_style_change(user_id: str, original_word: str, edited_word: str):
    """从风格调整中学习偏好"""
    try:
        from database import profiles_db

        # 检测正式度变化
        if len(edited_word) > len(original_word):
            profiles_db.record_preference(user_id, "formality_level", "formal")
        elif len(edited_word) < len(original_word):
            profiles_db.record_preference(user_id, "conciseness", "concise")

        # 检测口语→书面
        for oral, written in ORAL_TO_WRITTEN.items():
            if original_word == oral and edited_word == written:
                profiles_db.record_preference(user_id, "style", "written")
                break
    except Exception as e:
        logger.debug(f"记录偏好失败: {e}")


def analyze_edits(original: str, edited: str, scene: str = "",
                  user_id: str = "default", session_id: str = "") -> dict:
    """
    全流程分析：compute diff → classify each change → execute learning → return result

    返回:
      {
        "has_changes": bool,
        "changes": [{"type":str, "original_word":str, "edited_word":str, "classification":str}, ...],
        "classifications": {"asr_fix": int, "style_change": int, ...},
        "learn_actions": [{"action": str, ...}, ...],
        "edit_type": str    # 整体编辑类型（按占比最多的分类）
      }
    """
    if original == edited:
        return {
            "has_changes": False,
            "changes": [],
            "classifications": {},
            "learn_actions": [],
            "edit_type": "none"
        }

    # Step 1: 计算 diff
    changes = compute_word_diff(original, edited)

    # Step 2: 对每处改动分类
    classifications = {}
    for change in changes:
        cls = classify_edit(change, scene)
        change["classification"] = cls
        classifications[cls] = classifications.get(cls, 0) + 1

    # Step 3: 执行学习动作
    learn_actions = []
    for change in changes:
        cls = change.get("classification", "")
        ow = change.get("original_word", "")
        ew = change.get("edited_word", "")

        if cls == "asr_fix" and ow and ew:
            action = _learn_from_asr_fix(user_id, ow, ew)
            learn_actions.append(action)
        elif cls == "style_change" and ow and ew:
            _learn_from_style_change(user_id, ow, ew)
            learn_actions.append({
                "learned": True,
                "action": "preference_recorded",
                "original": ow,
                "edited": ew
            })
        elif cls == "content_add":
            learn_actions.append({
                "learned": False,
                "action": "content_add_detected",
                "word": ew
            })
        elif cls == "content_delete":
            learn_actions.append({
                "learned": False,
                "action": "content_delete_detected",
                "word": ow
            })

    # 确定整体编辑类型
    dominant_type = "style_change"
    if classifications:
        dominant_type = max(classifications, key=classifications.get)

    # Step 4: 记录到 edit_log_db
    try:
        from database import edit_log_db
        edit_log_db.log_edit(
            user_id=user_id,
            original_text=original,
            edited_text=edited,
            edit_type=dominant_type,
            diff_operations=changes,
            scene_type=scene,
            session_id=session_id
        )
    except Exception as e:
        logger.debug(f"写入 edit_log 失败: {e}")

    # Step 5: 记录场景使用
    try:
        from database import profiles_db
        profiles_db.record_scene_usage(user_id, scene or "通用")
        profiles_db.increment_stat(user_id, "total_corrections")
    except Exception as e:
        logger.debug(f"记录场景统计失败: {e}")

    return {
        "has_changes": True,
        "changes": changes,
        "classifications": classifications,
        "learn_actions": learn_actions,
        "edit_type": dominant_type
    }
