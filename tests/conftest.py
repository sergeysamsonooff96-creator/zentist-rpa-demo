import sys
import sqlite3
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture
def sqlite_conn(tmp_path: Path):
    db_path = tmp_path / "test_app.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE item_results (
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
        """
    )
    conn.commit()
    yield conn
    conn.close()