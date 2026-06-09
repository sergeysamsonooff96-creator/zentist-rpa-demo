import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.app.connectors.email_connector import EmailConnector


def test_email_connector_sends_report_with_attachment(tmp_path):
    report_path = tmp_path / "orangehrm_report.json"
    report_payload = {
        "portal": "orangehrm",
        "run_id": "run-100",
        "generated_at": "2026-06-08T10:00:00+03:00",
        "statistics": {
            "total": 2,
            "success": 1,
            "failed": 1,
        },
        "items": [
            {
                "item": {"first_name": "Alice", "last_name": "Ivanova"},
                "status": "success",
                "reason": "",
            },
            {
                "item": {"first_name": "Bob", "last_name": "Petrov"},
                "status": "failed",
                "reason": "Timeout",
            },
        ],
        "logs": [],
    }
    report_path.write_text(json.dumps(report_payload), encoding="utf-8")

    connector = EmailConnector(
        host="smtp.gmail.com",
        port=587,
        username="bot@example.com",
        password="secret",
        use_tls=True,
        from_email="bot@example.com",
    )

    with patch("smtplib.SMTP") as smtp_cls:
        smtp_instance = MagicMock()
        smtp_cls.return_value.__enter__.return_value = smtp_instance

        result = connector.send_report(
            recipient="recipient@example.com",
            report_path=str(report_path),
            report_payload=report_payload,
        )

        smtp_cls.assert_called_once_with("smtp.gmail.com", 587, timeout=30)
        smtp_instance.starttls.assert_called_once()
        smtp_instance.login.assert_called_once_with("bot@example.com", "secret")
        smtp_instance.send_message.assert_called_once()

        sent_message = smtp_instance.send_message.call_args[0][0]
        assert sent_message["To"] == "recipient@example.com"
        assert sent_message["From"] == "bot@example.com"
        assert "Zentist RPA Report" in sent_message["Subject"]

        attachments = list(sent_message.iter_attachments())
        assert len(attachments) == 1
        assert attachments[0].get_filename() == "orangehrm_report.json"

        assert result["recipient"] == "recipient@example.com"