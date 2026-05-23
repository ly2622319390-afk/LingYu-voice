import sqlite3
import os
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASES_DIR = BASE_DIR / "databases"


def get_db_path(db_name: str) -> str:
    """Get the path for a specific database folder and file."""
    db_dir = DATABASES_DIR / db_name
    db_dir.mkdir(parents=True, exist_ok=True)
    return str(db_dir / f"{db_name}.db")


class DatabaseManager:
    """Manages multiple SQLite databases organized by function."""

    def __init__(self):
        self.connections: dict[str, sqlite3.Connection] = {}

    def get_connection(self, db_name: str) -> sqlite3.Connection:
        if db_name not in self.connections:
            db_path = get_db_path(db_name)
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self.connections[db_name] = conn
        return self.connections[db_name]

    def close_all(self):
        for conn in self.connections.values():
            conn.close()
        self.connections.clear()


db_manager = DatabaseManager()
