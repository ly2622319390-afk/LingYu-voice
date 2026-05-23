"""历史记录数据库 - databases/history/history.db"""
from .db_manager import db_manager

DB_NAME = "history"


def init_db():
    conn = db_manager.get_connection(DB_NAME)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS history_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'default',
            content_raw TEXT NOT NULL,
            content_optimized TEXT DEFAULT '',
            scene_type TEXT DEFAULT '',
            title TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()


def save_history(user_id: str, content_raw: str, content_optimized: str = "",
                 scene_type: str = "", title: str = "", tags: str = "") -> dict:
    conn = db_manager.get_connection(DB_NAME)
    cur = conn.execute("""
        INSERT INTO history_items (user_id, content_raw, content_optimized, scene_type, title, tags)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, content_raw, content_optimized, scene_type, title, tags))
    conn.commit()
    return {"id": cur.lastrowid, "status": "saved"}


def get_history(user_id: str = "default", scene_type: str = "",
                page: int = 1, page_size: int = 20) -> dict:
    conn = db_manager.get_connection(DB_NAME)
    offset = (page - 1) * page_size
    if scene_type:
        rows = conn.execute(
            "SELECT * FROM history_items WHERE user_id=? AND scene_type=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (user_id, scene_type, page_size, offset)
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) as cnt FROM history_items WHERE user_id=? AND scene_type=?",
            (user_id, scene_type)
        ).fetchone()["cnt"]
    else:
        rows = conn.execute(
            "SELECT * FROM history_items WHERE user_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (user_id, page_size, offset)
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) as cnt FROM history_items WHERE user_id=?", (user_id,)
        ).fetchone()["cnt"]
    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


def delete_history(item_id: int) -> bool:
    conn = db_manager.get_connection(DB_NAME)
    cur = conn.execute("DELETE FROM history_items WHERE id=?", (item_id,))
    conn.commit()
    return cur.rowcount > 0


def get_history_detail(item_id: int) -> dict | None:
    conn = db_manager.get_connection(DB_NAME)
    row = conn.execute("SELECT * FROM history_items WHERE id=?", (item_id,)).fetchone()
    return dict(row) if row else None
