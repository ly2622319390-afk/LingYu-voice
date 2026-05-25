"""编辑日志数据库 — 记录用户每次编辑操作"""

import json
import logging
from .db_manager import db_manager

logger = logging.getLogger("voice-input.edit_log")

DB_NAME = "profiles"


def init_db():
    conn = db_manager.get_connection(DB_NAME)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS edit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'default',
            session_id TEXT DEFAULT '',
            scene_type TEXT DEFAULT '',
            original_text TEXT NOT NULL,
            edited_text TEXT NOT NULL,
            edit_type TEXT NOT NULL,
            diff_operations TEXT NOT NULL,
            is_reoptimized INTEGER DEFAULT 0,
            accepted_version TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_edit_log_user_time
        ON edit_log(user_id, created_at)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_edit_log_type
        ON edit_log(edit_type)
    """)
    conn.commit()


def log_edit(user_id: str, original_text: str, edited_text: str,
             edit_type: str, diff_operations: list,
             scene_type: str = "", session_id: str = "") -> int:
    """记录一条编辑日志，返回 id"""
    conn = db_manager.get_connection(DB_NAME)
    cur = conn.execute("""
        INSERT INTO edit_log (user_id, session_id, scene_type,
                              original_text, edited_text,
                              edit_type, diff_operations)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, session_id, scene_type,
          original_text, edited_text,
          edit_type, json.dumps(diff_operations, ensure_ascii=False)))
    conn.commit()
    return cur.lastrowid


def mark_reoptimized(edit_id: int):
    """标记某次编辑被用于重新生成了推荐"""
    conn = db_manager.get_connection(DB_NAME)
    conn.execute("UPDATE edit_log SET is_reoptimized = 1 WHERE id = ?", (edit_id,))
    conn.commit()


def get_edit_history(user_id: str, limit: int = 50) -> list[dict]:
    conn = db_manager.get_connection(DB_NAME)
    rows = conn.execute("""
        SELECT * FROM edit_log WHERE user_id=?
        ORDER BY created_at DESC LIMIT ?
    """, (user_id, limit)).fetchall()
    return [_parse_row(r) for r in rows]


def get_edits_by_type(user_id: str, edit_type: str, limit: int = 20) -> list[dict]:
    conn = db_manager.get_connection(DB_NAME)
    rows = conn.execute("""
        SELECT * FROM edit_log WHERE user_id=? AND edit_type=?
        ORDER BY created_at DESC LIMIT ?
    """, (user_id, edit_type, limit)).fetchall()
    return [_parse_row(r) for r in rows]


def get_recent_asr_fixes(user_id: str, limit: int = 50) -> list[dict]:
    """获取近期 ASR 修正记录，用于热词学习"""
    conn = db_manager.get_connection(DB_NAME)
    rows = conn.execute("""
        SELECT * FROM edit_log
        WHERE user_id=? AND edit_type='asr_fix'
        ORDER BY created_at DESC LIMIT ?
    """, (user_id, limit)).fetchall()
    return [_parse_row(r) for r in rows]


def _parse_row(row) -> dict:
    d = dict(row)
    if isinstance(d.get("diff_operations"), str):
        d["diff_operations"] = json.loads(d["diff_operations"])
    return d
