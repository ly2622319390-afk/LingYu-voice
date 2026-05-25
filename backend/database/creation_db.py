"""创作工作区数据库 — 会话 + 轮次持久化"""

import json
import logging
from .db_manager import db_manager

logger = logging.getLogger("voice-input.creation_db")

DB_NAME = "creation"


def init_db():
    conn = db_manager.get_connection(DB_NAME)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS creation_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'default',
            session_id TEXT UNIQUE NOT NULL,
            mode TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            round_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            finished_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS creation_rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            round_number INTEGER NOT NULL,
            raw_input TEXT NOT NULL,
            organized_output TEXT NOT NULL,
            extraction_json TEXT DEFAULT '{}',
            tips_json TEXT DEFAULT '[]',
            innovations_json TEXT DEFAULT '[]',
            improvements_json TEXT DEFAULT '[]',
            user_copied_organized INTEGER DEFAULT 0,
            user_copied_raw INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (session_id) REFERENCES creation_sessions(session_id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_creation_sessions_user
        ON creation_sessions(user_id, status)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_creation_rounds_session
        ON creation_rounds(session_id, round_number)
    """)
    conn.commit()


def save_session(session_id: str, mode: str, user_id: str = "default") -> dict:
    conn = db_manager.get_connection(DB_NAME)
    conn.execute(
        "INSERT OR IGNORE INTO creation_sessions (session_id, mode, user_id) VALUES (?, ?, ?)",
        (session_id, mode, user_id),
    )
    conn.commit()
    return {"session_id": session_id, "mode": mode, "status": "active"}


def finish_session_in_db(session_id: str) -> bool:
    conn = db_manager.get_connection(DB_NAME)
    cur = conn.execute(
        "UPDATE creation_sessions SET status='finished', finished_at=datetime('now','localtime') WHERE session_id=?",
        (session_id,),
    )
    conn.commit()
    return cur.rowcount > 0


def save_round(session_id: str, round_number: int, raw_input: str,
               organized_output: str, extraction: dict, tips: list,
               innovations: list, improvements: list) -> int:
    conn = db_manager.get_connection(DB_NAME)
    conn.execute(
        "UPDATE creation_sessions SET round_count = ? WHERE session_id = ?",
        (round_number, session_id),
    )
    cur = conn.execute("""
        INSERT INTO creation_rounds
            (session_id, round_number, raw_input, organized_output,
             extraction_json, tips_json, innovations_json, improvements_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id, round_number, raw_input, organized_output,
        json.dumps(extraction, ensure_ascii=False),
        json.dumps(tips, ensure_ascii=False),
        json.dumps(innovations, ensure_ascii=False),
        json.dumps(improvements, ensure_ascii=False),
    ))
    conn.commit()
    return cur.lastrowid


def update_copy_status(session_id: str, round_number: int, target: str):
    col = "user_copied_organized" if target == "organized" else "user_copied_raw"
    conn = db_manager.get_connection(DB_NAME)
    conn.execute(
        f"UPDATE creation_rounds SET {col}=1 WHERE session_id=? AND round_number=?",
        (session_id, round_number),
    )
    conn.commit()


def get_session_by_id(session_id: str) -> dict | None:
    conn = db_manager.get_connection(DB_NAME)
    row = conn.execute(
        "SELECT * FROM creation_sessions WHERE session_id=?", (session_id,)
    ).fetchone()
    return dict(row) if row else None


def get_rounds_by_session(session_id: str) -> list[dict]:
    conn = db_manager.get_connection(DB_NAME)
    rows = conn.execute(
        "SELECT * FROM creation_rounds WHERE session_id=? ORDER BY round_number ASC",
        (session_id,),
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        for field in ("extraction_json", "tips_json", "innovations_json", "improvements_json"):
            if isinstance(d.get(field), str):
                d[field.replace("_json", "")] = json.loads(d[field])
            del d[field]
        result.append(d)
    return result


def get_all_sessions(user_id: str = "default", status: str = "",
                     page: int = 1, page_size: int = 20) -> dict:
    conn = db_manager.get_connection(DB_NAME)
    where = "WHERE user_id=?"
    params = [user_id]
    if status:
        where += " AND status=?"
        params.append(status)
    total = conn.execute(
        f"SELECT COUNT(*) FROM creation_sessions {where}", params
    ).fetchone()[0]
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT * FROM creation_sessions {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()
    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }
