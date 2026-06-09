import asyncio
from uuid import uuid4

from src.app.config import get_settings
from src.app.logging import get_logger
from src.app.db.sqlite import get_connection, init_db
from src.app.db.repo import ResultRepository
from src.app.connectors.report_connector import ReportConnector
from src.app.connectors.email_connector import EmailConnector
from src.app.portals.registry import PORTAL_RUNNERS


async def main():
    settings = get_settings()
    logger = get_logger()

    logger.info(f"app_started portal={settings.portal_name}")

    conn = get_connection(settings.db_path)
    init_db(conn)
    repo = ResultRepository(conn)

    runner_cls = PORTAL_RUNNERS.get(settings.portal_name)
    if not runner_cls:
        raise ValueError(f"Unknown portal: {settings.portal_name}")

    run_id = str(uuid4())

    runner = runner_cls(
        config=settings,
        logger=logger,
        repo=repo,
        run_id=run_id,
    )

    await runner.run_job()

    report_connector = ReportConnector(conn)
    report_path, report_payload = report_connector.save_run_report(
        portal=runner.portal_name,
        run_id=run_id,
    )
    logger.info(f"report_saved path={report_path}")

    try:
        logger.info(
            f"email_step_started recipient={settings.report_email} "
            f"smtp_host={settings.smtp_host} smtp_port={settings.smtp_port}"
        )

        email_connector = EmailConnector(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            use_tls=settings.smtp_use_tls,
            from_email=settings.smtp_from,
        )

        email_result = email_connector.send_report(
            settings.report_email,
            report_path,
            report_payload,
        )

        logger.info(
            f"report_email_sent to={email_result.get('recipient', settings.report_email)} "
            f"status={email_result.get('status', 'sent')}"
        )
        logger.info("email_step_finished")
    except Exception as exc:
        logger.error(f"report_email_failed error={exc.__class__.__name__}")

    logger.info("app_finished")


if __name__ == "__main__":
    asyncio.run(main())