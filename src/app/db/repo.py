import json
import sqlite3
from datetime import datetime
from typing import Any


class ResultRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save_result(
        self,
        portal: str,
        run_id: str,
        item_key: str,
        status: str,
        reason: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        run_date = datetime.now().astimezone().strftime("%Y-%m-%d")

        self.conn.execute(
            """
            INSERT INTO item_results (
                portal, run_date, run_id, item_key, status, reason, payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(portal, run_date, item_key)
            DO UPDATE SET
                run_id=excluded.run_id,
                status=excluded.status,
                reason=excluded.reason,
                payload_json=excluded.payload_json
            """,
            (
                portal,
                run_date,
                run_id,
                item_key,
                status,
                reason,
                json.dumps(payload or {}, ensure_ascii=False),
            ),
        )
        self.conn.commit()