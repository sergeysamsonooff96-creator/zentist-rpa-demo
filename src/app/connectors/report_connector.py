import json
from datetime import datetime
from pathlib import Path


class ReportConnector:
    def __init__(self, conn) -> None:
        self.conn = conn

    def save_run_report(self, portal: str, run_id: str) -> tuple[str, dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT item_key, status, reason, payload_json, created_at
            FROM item_results
            WHERE portal = ? AND run_id = ?
            ORDER BY id
            """,
            (portal, run_id),
        )
        rows = cursor.fetchall()

        items = []
        success_count = 0
        failed_count = 0
        logs = []

        generated_at = datetime.now().astimezone()

        logs.append(
            {
                "timestamp": generated_at.isoformat(),
                "level": "INFO",
                "logger": "zentist_rpa",
                "event": "app_started",
                "message": f"app_started portal={portal}",
                "portal": portal,
                "run_id": run_id,
            }
        )
        logs.append(
            {
                "timestamp": generated_at.isoformat(),
                "level": "INFO",
                "logger": "zentist_rpa",
                "event": "job_started",
                "message": f"job_started portal={portal} run_id={run_id}",
                "portal": portal,
                "run_id": run_id,
            }
        )

        for item_key, status, reason, payload_json, created_at in rows:
            item_data = self._parse_item(item_key=item_key, payload_json=payload_json)

            if status == "success":
                success_count += 1
                event = "item_success"
                level = "INFO"
                message = f"item_success portal={portal}"
            else:
                failed_count += 1
                event = "item_failed"
                level = "ERROR"
                message = f"item_failed portal={portal} error={reason or ''}".strip()

            items.append(
                {
                    "item": item_data,
                    "status": status,
                    "reason": "" if status == "success" else (reason or ""),
                }
            )

            logs.append(
                {
                    "timestamp": created_at,
                    "level": level,
                    "logger": "zentist_rpa",
                    "event": event,
                    "message": message,
                    "portal": portal,
                    "run_id": run_id,
                    "item": item_data,
                    "reason": "" if status == "success" else (reason or ""),
                }
            )

        report_path_ts = generated_at.strftime("%Y-%m-%d_%H-%M-%S")

        logs.append(
            {
                "timestamp": generated_at.isoformat(),
                "level": "INFO",
                "logger": "zentist_rpa",
                "event": "job_finished",
                "message": f"job_finished portal={portal} run_id={run_id}",
                "portal": portal,
                "run_id": run_id,
            }
        )

        reports_dir = Path("reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / f"{portal}_{report_path_ts}.json"

        logs.append(
            {
                "timestamp": generated_at.isoformat(),
                "level": "INFO",
                "logger": "zentist_rpa",
                "event": "report_saved",
                "message": f"report_saved path={report_path}",
                "portal": portal,
                "run_id": run_id,
                "path": str(report_path),
            }
        )

        report_payload = {
            "portal": portal,
            "run_id": run_id,
            "generated_at": generated_at.isoformat(),
            "statistics": {
                "total": len(items),
                "success": success_count,
                "failed": failed_count,
            },
            "items": items,
            "logs": logs,
        }

        report_path.write_text(
            json.dumps(report_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return str(report_path), report_payload

    def _parse_item(self, item_key: str, payload_json: str | None) -> dict:
        if payload_json:
            try:
                parsed_payload = json.loads(payload_json)
                if isinstance(parsed_payload, dict):
                    return parsed_payload
            except json.JSONDecodeError:
                pass

        try:
            parsed_item_key = json.loads(item_key)
            if isinstance(parsed_item_key, dict):
                return parsed_item_key
        except json.JSONDecodeError:
            pass

        return {"raw_item": item_key}