import json
from pathlib import Path

from src.app.connectors.report_connector import ReportConnector


def test_report_connector_builds_json_report(sqlite_conn, tmp_path, monkeypatch):
    sqlite_conn.execute(
        """
        INSERT INTO item_results (
            portal, run_date, run_id, item_key, status, reason, payload_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "orangehrm",
            "2026-06-08",
            "run-42",
            json.dumps({"first_name": "Alice", "last_name": "Ivanova"}),
            "success",
            None,
            json.dumps(
                {
                    "first_name": "Alice",
                    "last_name": "Ivanova",
                    "job_title": "QA Engineer",
                    "employment_status": "Full-Time Permanent",
                }
            ),
        ),
    )
    sqlite_conn.execute(
        """
        INSERT INTO item_results (
            portal, run_date, run_id, item_key, status, reason, payload_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "orangehrm",
            "2026-06-08",
            "run-42",
            json.dumps({"first_name": "Bob", "last_name": "Petrov"}),
            "failed",
            "Page.goto timeout",
            json.dumps(
                {
                    "first_name": "Bob",
                    "last_name": "Petrov",
                    "job_title": "Business Analyst",
                    "employment_status": "Full-Time Contract",
                }
            ),
        ),
    )
    sqlite_conn.commit()

    monkeypatch.chdir(tmp_path)

    connector = ReportConnector(sqlite_conn)
    report_path, report_payload = connector.save_run_report(
        portal="orangehrm",
        run_id="run-42",
    )

    report_file = Path(report_path)
    assert report_file.exists()

    loaded_payload = json.loads(report_file.read_text(encoding="utf-8"))

    assert loaded_payload["portal"] == "orangehrm"
    assert loaded_payload["run_id"] == "run-42"
    assert loaded_payload["statistics"]["total"] == 2
    assert loaded_payload["statistics"]["success"] == 1
    assert loaded_payload["statistics"]["failed"] == 1

    assert len(loaded_payload["items"]) == 2
    assert loaded_payload["items"][0]["status"] == "success"
    assert loaded_payload["items"][1]["status"] == "failed"
    assert loaded_payload["items"][1]["reason"] == "Page.goto timeout"

    assert len(loaded_payload["logs"]) >= 4
    assert loaded_payload["logs"][0]["event"] == "app_started"
    assert any(log["event"] == "item_success" for log in loaded_payload["logs"])
    assert any(log["event"] == "item_failed" for log in loaded_payload["logs"])
    assert any(log["event"] == "report_saved" for log in loaded_payload["logs"])

    assert report_payload["statistics"]["total"] == 2