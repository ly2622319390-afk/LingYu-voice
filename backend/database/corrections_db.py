"""修正记录数据库 - databases/corrections/corrections.db"""
from .db_manager import db_manager
import sqlite3

DB_NAME = "corrections"


def init_db():
    conn = db_manager.get_connection(DB_NAME)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS correction_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'default',
            original_text TEXT DEFAULT '',
            corrected_text TEXT DEFAULT '',
            original_word TEXT NOT NULL,
            corrected_word TEXT NOT NULL,
            scene_type TEXT DEFAULT '',
            accepted_by_user INTEGER DEFAULT 1,
            timestamp TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()


def log_correction(user_id: str, original_word: str, corrected_word: str,
                   scene_type: str = "", original_text: str = "", corrected_text: str = "") -> dict:
    conn = db_manager.get_connection(DB_NAME)
    cur = conn.execute("""
        INSERT INTO correction_log (user_id, original_word, corrected_word, scene_type, original_text, corrected_text)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, original_word, corrected_word, scene_type, original_text, corrected_text))
    conn.commit()
    return {"id": cur.lastrowid, "status": "logged"}


def get_history(user_id: str = "default", limit: int = 50) -> list[dict]:
    conn = db_manager.get_connection(DB_NAME)
    rows = conn.execute(
        "SELECT * FROM correction_log WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    return [dict(r) for r in rows]


def get_frequent_corrections(user_id: str = "default", limit: int = 20) -> list[dict]:
    conn = db_manager.get_connection(DB_NAME)
    rows = conn.execute("""
        SELECT original_word, corrected_word, COUNT(*) as freq
        FROM correction_log
        WHERE user_id=? AND accepted_by_user=1
        GROUP BY original_word, corrected_word
        ORDER BY freq DESC LIMIT ?
    """, (user_id, limit)).fetchall()
    return [dict(r) for r in rows]
