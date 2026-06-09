import json

from src.app.db.repo import ResultRepository


def test_result_repository_persists_item_outcomes(sqlite_conn):
    repo = ResultRepository(sqlite_conn)

    repo.save_result(
        portal="orangehrm",
        run_id="run-1",
        item_key=json.dumps({"first_name": "Alice", "last_name": "Ivanova"}, ensure_ascii=False),
        status="success",
        reason=None,
        payload={
            "first_name": "Alice",
            "last_name": "Ivanova",
            "job_title": "QA Engineer",
            "employment_status": "Full-Time Permanent",
        },
    )

    repo.save_result(
        portal="orangehrm",
        run_id="run-1",
        item_key=json.dumps({"first_name": "Bob", "last_name": "Petrov"}, ensure_ascii=False),
        status="failed",
        reason="Page timeout",
        payload={
            "first_name": "Bob",
            "last_name": "Petrov",
            "job_title": "Business Analyst",
            "employment_status": "Full-Time Contract",
        },
    )

    rows = sqlite_conn.execute(
        """
        SELECT portal, run_id, item_key, status, reason, payload_json
        FROM item_results
        ORDER BY id
        """
    ).fetchall()

    assert len(rows) == 2
    assert rows[0][0] == "orangehrm"
    assert rows[0][1] == "run-1"
    assert rows[0][3] == "success"
    assert rows[0][4] is None

    first_payload = json.loads(rows[0][5])
    assert first_payload["first_name"] == "Alice"
    assert first_payload["job_title"] == "QA Engineer"

    assert rows[1][3] == "failed"
    assert rows[1][4] == "Page timeout"

    second_payload = json.loads(rows[1][5])
    assert second_payload["first_name"] == "Bob"
    assert second_payload["employment_status"] == "Full-Time Contract"


def test_result_repository_upserts_same_item_same_day(sqlite_conn):
    repo = ResultRepository(sqlite_conn)
    item_key = json.dumps({"account": "standard_user"}, ensure_ascii=False)

    repo.save_result(
        portal="saucedemo",
        run_id="run-1",
        item_key=item_key,
        status="failed",
        reason="Initial failure",
        payload={
            "account": "standard_user",
            "detail_stage": "Authorization",
        },
    )

    repo.save_result(
        portal="saucedemo",
        run_id="run-2",
        item_key=item_key,
        status="success",
        reason=None,
        payload={
            "account": "standard_user",
            "detail_stage": "Completed",
            "order_status": "completed",
        },
    )

    rows = sqlite_conn.execute(
        """
        SELECT portal, run_id, item_key, status, reason, payload_json
        FROM item_results
        """
    ).fetchall()

    assert len(rows) == 1
    assert rows[0][0] == "saucedemo"
    assert rows[0][1] == "run-2"
    assert rows[0][3] == "success"
    assert rows[0][4] is None

    payload = json.loads(rows[0][5])
    assert payload["account"] == "standard_user"
    assert payload["detail_stage"] == "Completed"
    assert payload["order_status"] == "completed"