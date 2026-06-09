import sqlite3
from pathlib import Path


def get_connection(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS item_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        portal TEXT NOT NULL,
        run_date TEXT NOT NULL,
        run_id TEXT NOT NULL,
        item_key TEXT NOT NULL,
        status TEXT NOT NULL,
        reason TEXT,
        payload_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(portal, run_date, item_key)
    )
    """)
    conn.commit()