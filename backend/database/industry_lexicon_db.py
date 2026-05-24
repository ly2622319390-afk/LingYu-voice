"""行业专业词库数据库 — 增强版 (v2.0)

比旧版 industry_lexicon 表更完善的 schema:
  - aliases: 常见误识别映射（用于 ASR 纠错）
  - weight: 专业词重要度
  - language: 语言标记
  - frequency: 使用频率
  - embedding: 向量缓存
"""
import json
import sqlite3
from .db_manager import db_manager

DB_NAME = "lexicon"  # 与现有词库共用同一个数据库文件


def init_db():
    conn = db_manager.get_connection(DB_NAME)
    # 主词条表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS industry_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            aliases TEXT DEFAULT '[]',       -- JSON 数组: ["蓝链","lang chain"]
            industry TEXT NOT NULL,            -- 行业分类
            sub_industry TEXT DEFAULT '',      -- 子行业
            weight REAL DEFAULT 0.8,           -- 专业词重要度 0~1
            type TEXT DEFAULT '',              -- framework / tool / concept / brand / ...
            language TEXT DEFAULT 'zh',        -- en / zh / mixed
            frequency REAL DEFAULT 0.5,        -- 使用频率 0~1
            description TEXT DEFAULT '',       -- 简短描述
            category TEXT DEFAULT '专业层',      -- 基础层/专业层/办公层/黑话层
            embedding BLOB DEFAULT NULL,       -- 向量缓存
            created_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(word, industry)
        )
    """)
    # 用户行业选择表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_industries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'default',
            industries TEXT DEFAULT '[]',       -- JSON 数组: ["互联网/AI","游戏"]
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    # 误识别映射表（用户学习）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS misrecognition_map (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'default',
            wrong TEXT NOT NULL,                -- 错误识别文本
            correct TEXT NOT NULL,              -- 正确词
            count INTEGER DEFAULT 1,            -- 出现次数
            last_seen TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(user_id, wrong, correct)
        )
    """)
    # 兼容：旧表无 category 列时补充
    try:
        conn.execute("ALTER TABLE industry_words ADD COLUMN category TEXT DEFAULT '专业层'")
    except sqlite3.OperationalError:
        pass
    conn.commit()


# ─── 行业词条 CRUD ─────────────────────────────────────────────

def add_industry_words(words: list[dict]):
    """批量导入行业词条"""
    conn = db_manager.get_connection(DB_NAME)
    count = 0
    for w in words:
        try:
            conn.execute("""
                INSERT OR REPLACE INTO industry_words
                    (word, aliases, industry, sub_industry, weight, type, language, frequency, description, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                w["word"],
                json.dumps(w.get("aliases", []), ensure_ascii=False),
                w.get("industry", ""),
                w.get("sub_industry", ""),
                w.get("weight", 0.8),
                w.get("type", ""),
                w.get("language", "zh"),
                w.get("frequency", 0.5),
                w.get("description", ""),
                w.get("category", "专业层"),
            ))
            count += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    return count


def get_industry_words(industry: str) -> list[dict]:
    """按行业获取词条"""
    conn = db_manager.get_connection(DB_NAME)
    rows = conn.execute(
        "SELECT * FROM industry_words WHERE industry=? ORDER BY weight DESC, frequency DESC",
        (industry,)
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_all_industries() -> list[str]:
    """获取所有已存在的行业分类"""
    import logging
    logger = logging.getLogger("voice-input.industry-lexicon-db")
    conn = db_manager.get_connection(DB_NAME)
    rows = conn.execute(
        "SELECT DISTINCT industry FROM industry_words ORDER BY industry"
    ).fetchall()
    result = [r["industry"] for r in rows]
    if not result:
        # 调试：检查表是否存在
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r["name"] for r in cur.fetchall()]
        cur2 = conn.execute("SELECT COUNT(*) as cnt FROM industry_words")
        cnt = cur2.fetchone()["cnt"]
        logger.warning(f"get_all_industries 返回空! 表={tables}, industry_words行数={cnt}")
    return result


def search_industry_words(keyword: str, industry: str = "") -> list[dict]:
    """搜索行业词条"""
    conn = db_manager.get_connection(DB_NAME)
    if industry:
        rows = conn.execute(
            "SELECT * FROM industry_words WHERE industry=? AND word LIKE ? ORDER BY weight DESC",
            (industry, f"%{keyword}%")
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM industry_words WHERE word LIKE ? ORDER BY weight DESC",
            (f"%{keyword}%",)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_words_for_hotwords(industries: list[str]) -> list[dict]:
    """获取指定行业的热词列表（供 HotwordManager 使用）"""
    conn = db_manager.get_connection(DB_NAME)
    if not industries:
        return []
    placeholders = ",".join("?" for _ in industries)
    rows = conn.execute(
        f"SELECT word, weight, frequency, industry FROM industry_words WHERE industry IN ({placeholders}) ORDER BY weight DESC LIMIT 200",
        industries
    ).fetchall()
    return [dict(r) for r in rows]


def get_words_by_category(industry: str, category: str) -> list[dict]:
    """按行业+层级分类获取词条"""
    conn = db_manager.get_connection(DB_NAME)
    rows = conn.execute(
        "SELECT * FROM industry_words WHERE industry=? AND category=? ORDER BY weight DESC, frequency DESC",
        (industry, category)
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_category_counts(industry: str) -> dict[str, int]:
    """获取某行业各层级的词条数量统计"""
    conn = db_manager.get_connection(DB_NAME)
    rows = conn.execute(
        "SELECT category, COUNT(*) as cnt FROM industry_words WHERE industry=? GROUP BY category ORDER BY cnt DESC",
        (industry,)
    ).fetchall()
    return {r["category"]: r["cnt"] for r in rows}


def get_alias_map(industries: list[str]) -> dict[str, str]:
    """获取行业词条的误识别映射表: 常见错误 → 正确词"""
    conn = db_manager.get_connection(DB_NAME)
    if not industries:
        return {}
    placeholders = ",".join("?" for _ in industries)
    rows = conn.execute(
        f"SELECT word, aliases FROM industry_words WHERE industry IN ({placeholders})",
        industries
    ).fetchall()
    mapping = {}
    for r in rows:
        word = r["word"]
        aliases = json.loads(r["aliases"])
        for alias in aliases:
            mapping[alias.lower()] = word
    return mapping


# ─── 用户行业选择 ─────────────────────────────────────────────

def set_user_industries(user_id: str, industries: list[str]):
    """设置用户选择的行业"""
    conn = db_manager.get_connection(DB_NAME)
    conn.execute("""
        INSERT OR REPLACE INTO user_industries (user_id, industries, updated_at)
        VALUES (?, ?, datetime('now','localtime'))
    """, (user_id, json.dumps(industries, ensure_ascii=False)))
    conn.commit()


def get_user_industries(user_id: str) -> list[str]:
    """获取用户选择的行业列表"""
    conn = db_manager.get_connection(DB_NAME)
    row = conn.execute(
        "SELECT industries FROM user_industries WHERE user_id=?", (user_id,)
    ).fetchone()
    if row:
        return json.loads(row["industries"])
    return []


# ─── 用户误识别学习 ──────────────────────────────────────────

def record_misrecognition(user_id: str, wrong: str, correct: str):
    """记录用户修正的误识别"""
    conn = db_manager.get_connection(DB_NAME)
    try:
        conn.execute("""
            INSERT INTO misrecognition_map (user_id, wrong, correct, count, last_seen)
            VALUES (?, ?, ?, 1, datetime('now','localtime'))
        """, (user_id, wrong, correct))
    except sqlite3.IntegrityError:
        conn.execute("""
            UPDATE misrecognition_map SET count = count + 1, last_seen = datetime('now','localtime')
            WHERE user_id=? AND wrong=? AND correct=?
        """, (user_id, wrong, correct))
    conn.commit()


def get_user_correction_map(user_id: str) -> dict[str, str]:
    """获取用户积累的误识别映射"""
    conn = db_manager.get_connection(DB_NAME)
    rows = conn.execute("""
        SELECT wrong, correct FROM misrecognition_map
        WHERE user_id=? ORDER BY count DESC LIMIT 100
    """, (user_id,)).fetchall()
    return {r["wrong"].lower(): r["correct"] for r in rows}


def _row_to_dict(row) -> dict:
    d = dict(row)
    if isinstance(d.get("aliases"), str):
        d["aliases"] = json.loads(d["aliases"])
    if d.get("embedding"):
        d.pop("embedding")  # 不返回二进制数据
    return d


# ─── 启动时检查：如果表为空则自动导入 ───
def ensure_seeded():
    """确保行业词库有种子数据（只运行一次）"""
    conn = db_manager.get_connection(DB_NAME)
    cur = conn.execute("SELECT COUNT(*) as cnt FROM industry_words")
    count = cur.fetchone()["cnt"]
    if count == 0:
        from .seed_industry_words import INDUSTRY_WORDS
        add_industry_words(INDUSTRY_WORDS)
        return len(INDUSTRY_WORDS)
    return count


# 模块加载时自动检查
_initial_count = ensure_seeded()
