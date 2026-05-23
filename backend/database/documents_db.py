"""文档导入来源数据库 - databases/documents/documents.db"""
from .db_manager import db_manager
import json

DB_NAME = "documents"


def init_db():
    conn = db_manager.get_connection(DB_NAME)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS document_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'default',
            file_name TEXT NOT NULL,
            file_type TEXT DEFAULT '',
            extracted_terms TEXT DEFAULT '[]',
            imported_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()


def save_document(user_id: str, file_name: str, file_type: str, extracted_terms: list[str]) -> dict:
    conn = db_manager.get_connection(DB_NAME)
    cur = conn.execute("""
        INSERT INTO document_sources (user_id, file_name, file_type, extracted_terms)
        VALUES (?, ?, ?, ?)
    """, (user_id, file_name, file_type, json.dumps(extracted_terms, ensure_ascii=False)))
    conn.commit()
    return {"id": cur.lastrowid, "status": "saved"}


def get_documents(user_id: str = "default") -> list[dict]:
    conn = db_manager.get_connection(DB_NAME)
    rows = conn.execute(
        "SELECT * FROM document_sources WHERE user_id=? ORDER BY imported_at DESC",
        (user_id,)
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["extracted_terms"] = json.loads(d["extracted_terms"])
        result.append(d)
    return result


def delete_document(doc_id: int) -> bool:
    conn = db_manager.get_connection(DB_NAME)
    cur = conn.execute("DELETE FROM document_sources WHERE id=?", (doc_id,))
    conn.commit()
    return cur.rowcount > 0
