"""用户词库数据库 - databases/lexicon/lexicon.db"""
import sqlite3
from .db_manager import db_manager

DB_NAME = "lexicon"


def init_db():
    conn = db_manager.get_connection(DB_NAME)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_lexicon (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'default',
            word TEXT NOT NULL,
            word_type TEXT DEFAULT '自定义',
            industry_tag TEXT DEFAULT '',
            source TEXT DEFAULT '手动添加',
            confidence REAL DEFAULT 0.8,
            usage_count INTEGER DEFAULT 0,
            last_used_at TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(user_id, word)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS industry_lexicon (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            word_type TEXT DEFAULT '',
            industry_tag TEXT NOT NULL,
            confidence REAL DEFAULT 0.9,
            UNIQUE(word, industry_tag)
        )
    """)
    conn.commit()


def get_all_words(user_id: str = "default") -> list[dict]:
    conn = db_manager.get_connection(DB_NAME)
    rows = conn.execute(
        "SELECT * FROM user_lexicon WHERE user_id=? ORDER BY usage_count DESC, last_used_at DESC",
        (user_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def add_word(user_id: str, word: str, word_type: str = "自定义",
             industry_tag: str = "", source: str = "手动添加") -> dict:
    conn = db_manager.get_connection(DB_NAME)
    try:
        cur = conn.execute("""
            INSERT INTO user_lexicon (user_id, word, word_type, industry_tag, source)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, word, word_type, industry_tag, source))
        conn.commit()
        return {"id": cur.lastrowid, "word": word, "status": "added"}
    except sqlite3.IntegrityError:
        conn.execute("""
            UPDATE user_lexicon SET usage_count = usage_count + 1, last_used_at = datetime('now','localtime')
            WHERE user_id=? AND word=?
        """, (user_id, word))
        conn.commit()
        row = conn.execute(
            "SELECT * FROM user_lexicon WHERE user_id=? AND word=?", (user_id, word)
        ).fetchone()
        result = dict(row) if row else {}
        result["status"] = "updated"
        return result


def delete_word(word_id: int) -> bool:
    conn = db_manager.get_connection(DB_NAME)
    cur = conn.execute("DELETE FROM user_lexicon WHERE id=?", (word_id,))
    conn.commit()
    return cur.rowcount > 0


def search_word(user_id: str, keyword: str) -> list[dict]:
    conn = db_manager.get_connection(DB_NAME)
    rows = conn.execute(
        "SELECT * FROM user_lexicon WHERE user_id=? AND word LIKE ? ORDER BY usage_count DESC",
        (user_id, f"%{keyword}%")
    ).fetchall()
    return [dict(r) for r in rows]


def get_industry_words(industry_tag: str) -> list[dict]:
    conn = db_manager.get_connection(DB_NAME)
    rows = conn.execute(
        "SELECT * FROM industry_lexicon WHERE industry_tag=? ORDER BY word", (industry_tag,)
    ).fetchall()
    return [dict(r) for r in rows]


def add_industry_words(words: list[dict]):
    conn = db_manager.get_connection(DB_NAME)
    for w in words:
        try:
            conn.execute("""
                INSERT INTO industry_lexicon (word, word_type, industry_tag, confidence)
                VALUES (?, ?, ?, ?)
            """, (w["word"], w.get("word_type", ""), w["industry_tag"], w.get("confidence", 0.9)))
        except sqlite3.IntegrityError:
            pass
    conn.commit()


def check_known_word(user_id: str, word: str) -> dict | None:
    """Check word against user lexicon first, then industry lexicon."""
    conn = db_manager.get_connection(DB_NAME)
    row = conn.execute(
        "SELECT * FROM user_lexicon WHERE user_id=? AND word=?", (user_id, word)
    ).fetchone()
    if row:
        return dict(row) | {"source": "user_lexicon"}
    row = conn.execute(
        "SELECT * FROM industry_lexicon WHERE word=?", (word,)
    ).fetchone()
    if row:
        return dict(row) | {"source": "industry_lexicon"}
    return None
