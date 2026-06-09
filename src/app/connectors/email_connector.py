import html
import re
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any


class EmailConnector:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        use_tls: bool,
        from_email: str,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.from_email = from_email

    def _parse_error_reason(self, reason: str) -> tuple[str, str, str]:
        if not reason:
            return "—", "—", "—"

        item_match = re.search(r"item_label=([^;]+)", reason)
        item_label = item_match.group(1).strip() if item_match else "—"

        stages = re.findall(r"\[([^\]]+)\]", reason)
        detail_stage = "—"
        if len(stages) >= 2:
            detail_stage = stages[1].strip()
        elif len(stages) == 1:
            detail_stage = stages[0].strip()

        cleaned_reason = re.sub(r"\[[^\]]+\]\s*", "", reason).strip()
        cleaned_reason = re.sub(r"item_label=([^;]+);\s*", "", cleaned_reason).strip()
        cleaned_reason = cleaned_reason or "—"

        return item_label, detail_stage, cleaned_reason

    def _normalize_item(self, item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            return item
        if isinstance(item, str):
            return {"account": item, "item_label": item}
        return {}

    def _format_item_name(self, item: dict[str, Any]) -> str:
        if not item:
            return "—"

        item_label = str(item.get("item_label", "")).strip()
        if item_label:
            return item_label

        first_name = str(item.get("first_name", "")).strip()
        last_name = str(item.get("last_name", "")).strip()
        full_name = f"{first_name} {last_name}".strip()
        if full_name:
            return full_name

        account = str(item.get("account", "")).strip()
        if account:
            return account

        return "—"

    def _format_success_details(self, item: dict[str, Any]) -> str:
        if not item:
            return "Completed"

        detail_stage = str(item.get("detail_stage", "")).strip()
        if detail_stage:
            return detail_stage

        if item.get("account"):
            return "Checkout Completed"

        if item.get("job_title") or item.get("employment_status"):
            return "Employee Data Update Completed"

        return "Completed"

    def _render_failed_rows(self, items: list[dict[str, Any]]) -> str:
        failed_items = [x for x in items if x.get("status") != "success"]

        if not failed_items:
            return """
            <tr>
              <td colspan="4" style="padding:14px 16px; border-bottom:1px solid #e5e7eb; color:#6b7280;">
                No failed items
              </td>
            </tr>
            """

        rows = []
        for row in failed_items:
            raw_item = self._normalize_item(row.get("item"))
            raw_reason = str(row.get("reason") or "")

            parsed_item, parsed_stage, parsed_reason = self._parse_error_reason(raw_reason)

            item_name = parsed_item if parsed_item != "—" else self._format_item_name(raw_item)
            details = parsed_stage if parsed_stage != "—" else "Failed"

            rows.append(
                f"""
                <tr>
                  <td style="padding:14px 16px; border-bottom:1px solid #e5e7eb; vertical-align:top; width:90px;">
                    <span style="display:inline-block; padding:4px 10px; background:#fef2f2; color:#b91c1c; border:1px solid #fecaca; border-radius:999px; font-size:12px; font-weight:700;">
                      Failed
                    </span>
                  </td>
                  <td style="padding:14px 16px; border-bottom:1px solid #e5e7eb; vertical-align:top; font-weight:600; color:#111827;">
                    {html.escape(item_name)}
                  </td>
                  <td style="padding:14px 16px; border-bottom:1px solid #e5e7eb; vertical-align:top; color:#374151;">
                    {html.escape(details)}
                  </td>
                  <td style="padding:14px 16px; border-bottom:1px solid #e5e7eb; vertical-align:top;">
                    <div style="display:inline-block; background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px; padding:10px 12px; color:#374151; line-height:1.45;">
                      {html.escape(parsed_reason)}
                    </div>
                  </td>
                </tr>
                """
            )

        return "".join(rows)

    def _render_success_rows(self, items: list[dict[str, Any]]) -> str:
        success_items = [x for x in items if x.get("status") == "success"]

        if not success_items:
            return """
            <tr>
              <td colspan="4" style="padding:14px 16px; border-bottom:1px solid #e5e7eb; color:#6b7280;">
                No successful items
              </td>
            </tr>
            """

        rows = []
        for row in success_items:
            raw_item = self._normalize_item(row.get("item"))
            item_name = self._format_item_name(raw_item)
            details = self._format_success_details(raw_item)

            rows.append(
                f"""
                <tr>
                  <td style="padding:14px 16px; border-bottom:1px solid #e5e7eb; vertical-align:top; width:90px;">
                    <span style="display:inline-block; padding:4px 10px; background:#ecfdf5; color:#047857; border:1px solid #a7f3d0; border-radius:999px; font-size:12px; font-weight:700;">
                      Success
                    </span>
                  </td>
                  <td style="padding:14px 16px; border-bottom:1px solid #e5e7eb; vertical-align:top; font-weight:600; color:#111827;">
                    {html.escape(item_name)}
                  </td>
                  <td style="padding:14px 16px; border-bottom:1px solid #e5e7eb; vertical-align:top; color:#374151;">
                    {html.escape(details)}
                  </td>
                  <td style="padding:14px 16px; border-bottom:1px solid #e5e7eb; vertical-align:top; color:#374151;">
                    Completed successfully
                  </td>
                </tr>
                """
            )

        return "".join(rows)

    def _build_html_body(self, report_payload: dict[str, Any]) -> str:
        portal = str(report_payload.get("portal", "unknown"))
        run_id = str(report_payload.get("run_id", "unknown"))
        generated_at = str(report_payload.get("generated_at", "unknown"))

        statistics = report_payload.get("statistics") or {}
        total = statistics.get("total", 0)
        success = statistics.get("success", 0)
        failed = statistics.get("failed", 0)

        items = report_payload.get("items") or []
        if not isinstance(items, list):
            items = []

        success_rows = self._render_success_rows(items)
        failed_rows = self._render_failed_rows(items)

        return f"""
        <html>
          <body style="margin:0; padding:0; background:#f3f4f6; font-family:Arial, Helvetica, sans-serif; color:#111827;">
            <div style="width:100%; background:#f3f4f6; padding:24px 0;">
              <div style="max-width:960px; margin:0 auto; background:#ffffff; border:1px solid #e5e7eb; border-radius:16px; overflow:hidden;">

                <div style="background:#111827; padding:28px 32px;">
                  <div style="font-size:12px; letter-spacing:0.08em; text-transform:uppercase; color:#9ca3af; margin-bottom:8px;">
                    Zentist RPA
                  </div>
                  <h1 style="margin:0; font-size:28px; line-height:1.2; color:#ffffff;">
                    Automation Run Report
                  </h1>
                  <p style="margin:10px 0 0 0; font-size:15px; line-height:1.5; color:#d1d5db;">
                    Clear summary of what happened during the latest portal run.
                  </p>
                </div>

                <div style="padding:24px 32px 8px 32px;">
                  <table style="width:100%; border-collapse:collapse; margin-bottom:20px;">
                    <tr>
                      <td style="padding:0 0 10px 0; color:#6b7280; font-size:13px; width:140px;">Portal</td>
                      <td style="padding:0 0 10px 0; color:#111827; font-size:14px; font-weight:600;">{html.escape(portal)}</td>
                    </tr>
                    <tr>
                      <td style="padding:0 0 10px 0; color:#6b7280; font-size:13px;">Run ID</td>
                      <td style="padding:0 0 10px 0; color:#111827; font-size:14px; font-weight:600;">{html.escape(run_id)}</td>
                    </tr>
                    <tr>
                      <td style="padding:0 0 10px 0; color:#6b7280; font-size:13px;">Generated at</td>
                      <td style="padding:0 0 10px 0; color:#111827; font-size:14px; font-weight:600;">{html.escape(generated_at)}</td>
                    </tr>
                  </table>
                </div>

                <div style="padding:0 32px 8px 32px;">
                  <table style="width:100%; border-collapse:separate; border-spacing:12px 0;">
                    <tr>
                      <td style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:14px; padding:18px 20px; width:33.33%;">
                        <div style="font-size:12px; color:#6b7280; text-transform:uppercase; letter-spacing:0.06em;">Total</div>
                        <div style="font-size:28px; font-weight:700; color:#111827; margin-top:6px;">{total}</div>
                      </td>
                      <td style="background:#ecfdf5; border:1px solid #a7f3d0; border-radius:14px; padding:18px 20px; width:33.33%;">
                        <div style="font-size:12px; color:#047857; text-transform:uppercase; letter-spacing:0.06em;">Success</div>
                        <div style="font-size:28px; font-weight:700; color:#065f46; margin-top:6px;">{success}</div>
                      </td>
                      <td style="background:#fef2f2; border:1px solid #fecaca; border-radius:14px; padding:18px 20px; width:33.33%;">
                        <div style="font-size:12px; color:#b91c1c; text-transform:uppercase; letter-spacing:0.06em;">Failed</div>
                        <div style="font-size:28px; font-weight:700; color:#991b1b; margin-top:6px;">{failed}</div>
                      </td>
                    </tr>
                  </table>
                </div>

                <div style="padding:24px 32px 8px 32px;">
                  <h2 style="margin:0 0 12px 0; font-size:18px; color:#111827;">Successful transactions</h2>
                  <div style="border:1px solid #e5e7eb; border-radius:14px; overflow:hidden;">
                    <table style="width:100%; border-collapse:collapse; background:#ffffff;">
                      <tr style="background:#f9fafb;">
                        <th style="text-align:left; padding:14px 16px; font-size:12px; text-transform:uppercase; letter-spacing:0.06em; color:#6b7280; border-bottom:1px solid #e5e7eb;">Status</th>
                        <th style="text-align:left; padding:14px 16px; font-size:12px; text-transform:uppercase; letter-spacing:0.06em; color:#6b7280; border-bottom:1px solid #e5e7eb;">Item</th>
                        <th style="text-align:left; padding:14px 16px; font-size:12px; text-transform:uppercase; letter-spacing:0.06em; color:#6b7280; border-bottom:1px solid #e5e7eb;">Details</th>
                        <th style="text-align:left; padding:14px 16px; font-size:12px; text-transform:uppercase; letter-spacing:0.06em; color:#6b7280; border-bottom:1px solid #e5e7eb;">Reason</th>
                      </tr>
                      {success_rows}
                    </table>
                  </div>
                </div>

                <div style="padding:16px 32px 32px 32px;">
                  <h2 style="margin:0 0 12px 0; font-size:18px; color:#111827;">Failed transactions</h2>
                  <div style="border:1px solid #e5e7eb; border-radius:14px; overflow:hidden;">
                    <table style="width:100%; border-collapse:collapse; background:#ffffff;">
                      <tr style="background:#f9fafb;">
                        <th style="text-align:left; padding:14px 16px; font-size:12px; text-transform:uppercase; letter-spacing:0.06em; color:#6b7280; border-bottom:1px solid #e5e7eb;">Status</th>
                        <th style="text-align:left; padding:14px 16px; font-size:12px; text-transform:uppercase; letter-spacing:0.06em; color:#6b7280; border-bottom:1px solid #e5e7eb;">Item</th>
                        <th style="text-align:left; padding:14px 16px; font-size:12px; text-transform:uppercase; letter-spacing:0.06em; color:#6b7280; border-bottom:1px solid #e5e7eb;">Details</th>
                        <th style="text-align:left; padding:14px 16px; font-size:12px; text-transform:uppercase; letter-spacing:0.06em; color:#6b7280; border-bottom:1px solid #e5e7eb;">Reason</th>
                      </tr>
                      {failed_rows}
                    </table>
                  </div>
                </div>

              </div>
            </div>
          </body>
        </html>
        """

    def send_report(
        self,
        recipient: str,
        report_path: str,
        report_payload: dict[str, Any],
    ) -> dict[str, Any]:
        message = EmailMessage()
        message["Subject"] = f"Zentist RPA Report - {report_payload.get('portal', 'unknown')}"
        message["From"] = self.from_email
        message["To"] = recipient

        html_body = self._build_html_body(report_payload)
        message.set_content("Zentist RPA Report attached. Please use an HTML-capable email client.")
        message.add_alternative(html_body, subtype="html")

        attachment_path = Path(report_path)
        message.add_attachment(
            attachment_path.read_bytes(),
            maintype="application",
            subtype="json",
            filename=attachment_path.name,
        )

        with smtplib.SMTP(self.host, self.port, timeout=30) as smtp:
            if self.use_tls:
                smtp.starttls()
            smtp.login(self.username, self.password)
            smtp.send_message(message)

        return {
            "status": "sent",
            "recipient": recipient,
            "subject": message["Subject"],
            "attachment_name": attachment_path.name,
        }