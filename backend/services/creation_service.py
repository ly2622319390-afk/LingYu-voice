"""
交互式创作工作区 — 会话管理 + LLM 编排

功能:
  - 创建/获取/结束创作会话
  - 多轮语音输入 → LLM 处理 → 结构化输出
  - 规则降级（无 LLM 时）
"""

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Optional

logger = logging.getLogger("voice-input.creation")

_active_sessions: dict[str, "CreationSession"] = {}


class CreationRound:
    """一轮创作交互"""

    def __init__(self, round_number: int, raw_input: str,
                 organized_output: str = "", extraction: dict = None,
                 tips: list = None, innovations: list = None,
                 improvements: list = None):
        self.round_number = round_number
        self.raw_input = raw_input
        self.organized_output = organized_output
        self.extraction = extraction or {}
        self.tips = tips or []
        self.innovations = innovations or []
        self.improvements = improvements or []
        self.user_copied_organized = False
        self.user_copied_raw = False
        self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "round_number": self.round_number,
            "raw_input": self.raw_input,
            "organized_output": self.organized_output,
            "extraction": self.extraction,
            "tips": self.tips,
            "innovations": self.innovations,
            "improvements": self.improvements,
            "user_copied_organized": self.user_copied_organized,
            "user_copied_raw": self.user_copied_raw,
            "created_at": self.created_at,
        }


class CreationSession:
    """一个完整的创作会话（多轮）"""

    def __init__(self, mode: str):
        self.session_id = uuid.uuid4().hex[:8]
        self.mode = mode  # "novel" | "project"
        self.status = "active"
        self.rounds: list[CreationRound] = []
        self.created_at = datetime.now().isoformat()
        self.finished_at: Optional[str] = None

    @property
    def accumulated_context(self) -> str:
        """构建多轮累积上下文字符串"""
        if not self.rounds:
            return ""
        parts = []
        for r in self.rounds:
            parts.append(f"--- 第{r.round_number}轮 ---")
            parts.append(f"用户输入: {r.raw_input}")
            parts.append(f"整理内容: {r.organized_output[:200]}")
            if r.extraction:
                parts.append(f"提取要素: {json.dumps(r.extraction, ensure_ascii=False)[:200]}")
        return "\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "mode": self.mode,
            "status": self.status,
            "rounds": [r.to_dict() for r in self.rounds],
            "accumulated_context": self.accumulated_context,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
        }


# ─── 会话管理 ───


def create_session(mode: str) -> CreationSession:
    session = CreationSession(mode)
    _active_sessions[session.session_id] = session
    logger.info(f"创作会话已创建: {session.session_id} mode={mode}")
    return session


def get_session(session_id: str) -> Optional[CreationSession]:
    return _active_sessions.get(session_id)


def finish_session(session_id: str) -> Optional[CreationSession]:
    session = _active_sessions.get(session_id)
    if session:
        session.status = "finished"
        session.finished_at = datetime.now().isoformat()
    return session


def mark_copy_organized(session_id: str, round_number: int) -> bool:
    session = _active_sessions.get(session_id)
    if not session:
        return False
    for r in session.rounds:
        if r.round_number == round_number:
            r.user_copied_organized = True
            return True
    return False


def mark_copy_raw(session_id: str, round_number: int) -> bool:
    session = _active_sessions.get(session_id)
    if not session:
        return False
    for r in session.rounds:
        if r.round_number == round_number:
            r.user_copied_raw = True
            return True
    return False


# ─── 轮次处理 ───


def add_round(session_id: str, raw_input: str,
              llm_result: dict = None) -> CreationRound:
    """添加一轮（由调用方传入 LLM 或规则结果）"""
    session = _active_sessions.get(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    if llm_result is None:
        llm_result = {
            "extraction": {},
            "organized_output": raw_input,
            "tips": [],
            "innovations": [],
            "improvements": [],
        }

    round_number = len(session.rounds) + 1
    new_round = CreationRound(
        round_number=round_number,
        raw_input=raw_input,
        organized_output=llm_result.get("organized_output", raw_input),
        extraction=llm_result.get("extraction", {}),
        tips=llm_result.get("tips", []),
        innovations=llm_result.get("innovations", []),
        improvements=llm_result.get("improvements", []),
    )
    session.rounds.append(new_round)
    return new_round


def get_active_sessions() -> list[dict]:
    return [
        {"session_id": s.session_id, "mode": s.mode, "round_count": len(s.rounds)}
        for s in _active_sessions.values()
        if s.status == "active"
    ]


# ─── LLM 处理 ───


async def process_with_llm(session: CreationSession, new_input: str,
                           prompt_manager) -> dict:
    """调用 LLM 处理一轮输入"""
    template_name = "creation_novel" if session.mode == "novel" else "creation_project"
    profile_context = ""
    try:
        from services.profile_prompt_builder import build_full_context
        profile_context = build_full_context()
    except ImportError:
        pass

    accumulated = session.accumulated_context or "（尚无历史内容）"

    llm_output = await prompt_manager.execute(
        template_name,
        new_input=new_input,
        accumulated_context=accumulated,
        profile_context=profile_context,
        use_cache=False,
    )

    # Parse JSON from LLM output
    result = _parse_llm_json(llm_output)

    # Validate required fields
    for key in ("extraction", "organized_output", "tips", "innovations", "improvements"):
        if key not in result:
            result[key] = {} if key == "extraction" else ("" if key == "organized_output" else [])

    return result


def _parse_llm_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON"""
    # 尝试直接解析
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试从 markdown 代码块提取
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 尝试找到第一个 { 和最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError("无法从 LLM 输出中解析 JSON")


def rule_based_fallback(mode: str, text: str) -> dict:
    """无 LLM 时的规则降级处理"""
    extraction = {}
    if mode == "novel":
        extraction = {"genre": "未明确", "characters": [], "setting": "",
                      "plot_points": [text[:80]], "tone": "未明确", "themes": []}
    else:
        extraction = {"project_goal": text[:100], "target_users": [],
                      "core_features": [], "tech_stack": [], "constraints": [],
                      "project_type": "未明确"}

    return {
        "extraction": extraction,
        "organized_output": f"【规则模式】{text}\n\n（提示：启用大模型可获得更高质量的结构化整理）",
        "tips": ["尝试补充更多细节", "考虑从不同角度展开"],
        "innovations": ["（规则模式：请启用 LLM 获取创新建议）"],
        "improvements": ["（建议启用大模型获得更优结果）"],
    }
