"""持久化用户画像数据库 — 替代纯内存的 UserProfile

存储用户的偏好、编辑统计、场景使用记录，重启不丢失。
"""

import json
import logging
from .db_manager import db_manager

logger = logging.getLogger("voice-input.profiles")

DB_NAME = "profiles"


def init_db():
    conn = db_manager.get_connection(DB_NAME)
    # 用户画像总表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            total_sessions INTEGER DEFAULT 0,
            total_recordings INTEGER DEFAULT 0,
            total_corrections INTEGER DEFAULT 0,
            total_optimizations INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    # 用户偏好表（键值对 + 置信度）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'default',
            pref_key TEXT NOT NULL,
            pref_value TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            first_seen TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(user_id, pref_key, pref_value)
        )
    """)
    # 场景使用统计
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scene_usage_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'default',
            scene_type TEXT NOT NULL,
            usage_count INTEGER DEFAULT 0,
            last_used_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(user_id, scene_type)
        )
    """)
    conn.commit()


# ─── 用户画像 ─────────────────────────────────────────────

def get_or_create_profile(user_id: str) -> dict:
    conn = db_manager.get_connection(DB_NAME)
    row = conn.execute(
        "SELECT * FROM user_profiles WHERE user_id=?", (user_id,)
    ).fetchone()
    if row:
        return dict(row)
    conn.execute(
        "INSERT INTO user_profiles (user_id) VALUES (?)", (user_id,)
    )
    conn.commit()
    return {"user_id": user_id, "total_sessions": 0, "total_recordings": 0,
            "total_corrections": 0, "total_optimizations": 0}


def increment_stat(user_id: str, stat: str):
    """递增统计字段，如 total_corrections / total_optimizations"""
    conn = db_manager.get_connection(DB_NAME)
    conn.execute(
        f"UPDATE user_profiles SET {stat} = {stat} + 1, updated_at=datetime('now','localtime') WHERE user_id=?",
        (user_id,)
    )
    conn.commit()


# ─── 用户偏好 ─────────────────────────────────────────────

def record_preference(user_id: str, pref_key: str, pref_value: str):
    """记录或强化用户偏好（置信度递增）"""
    conn = db_manager.get_connection(DB_NAME)
    conn.execute("""
        INSERT INTO user_preferences (user_id, pref_key, pref_value, confidence)
        VALUES (?, ?, ?, 1.0)
        ON CONFLICT(user_id, pref_key, pref_value)
        DO UPDATE SET confidence = confidence + 0.5, updated_at = datetime('now','localtime')
    """, (user_id, pref_key, pref_value))
    conn.commit()


def get_preferences(user_id: str, top_k: int = 10) -> list[dict]:
    """获取用户偏好，按置信度降序"""
    conn = db_manager.get_connection(DB_NAME)
    rows = conn.execute(
        "SELECT * FROM user_preferences WHERE user_id=? ORDER BY confidence DESC LIMIT ?",
        (user_id, top_k)
    ).fetchall()
    return [dict(r) for r in rows]


def get_top_preferences(user_id: str, pref_key: str = "", top_k: int = 5) -> list[dict]:
    """获取指定类型的偏好（如 formality_level）"""
    conn = db_manager.get_connection(DB_NAME)
    if pref_key:
        rows = conn.execute(
            "SELECT * FROM user_preferences WHERE user_id=? AND pref_key=? ORDER BY confidence DESC LIMIT ?",
            (user_id, pref_key, top_k)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM user_preferences WHERE user_id=? ORDER BY confidence DESC LIMIT ?",
            (user_id, top_k)
        ).fetchall()
    return [dict(r) for r in rows]


# ─── 场景统计 ─────────────────────────────────────────────

def record_scene_usage(user_id: str, scene_type: str):
    conn = db_manager.get_connection(DB_NAME)
    conn.execute("""
        INSERT INTO scene_usage_stats (user_id, scene_type, usage_count, last_used_at)
        VALUES (?, ?, 1, datetime('now','localtime'))
        ON CONFLICT(user_id, scene_type)
        DO UPDATE SET usage_count = usage_count + 1, last_used_at = datetime('now','localtime')
    """, (user_id, scene_type))
    conn.commit()


def get_scene_usage(user_id: str) -> list[dict]:
    conn = db_manager.get_connection(DB_NAME)
    rows = conn.execute(
        "SELECT * FROM scene_usage_stats WHERE user_id=? ORDER BY usage_count DESC",
        (user_id,)
    ).fetchall()
    return [dict(r) for r in rows]
