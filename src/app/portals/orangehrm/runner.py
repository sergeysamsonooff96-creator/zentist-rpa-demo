from pathlib import Path
import tempfile

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from src.app.core.base_runner import BasePortalRunnerZX
from src.app.core.browser import BrowserSession
from src.app.portals.orangehrm.data import EMPLOYEES


class OrangeHRMRunner(BasePortalRunnerZX):
    @property
    def portal_name(self) -> str:
        return "orangehrm"

    def iter_items(self):
        return EMPLOYEES

    def _build_stage_error(self, stage: str, message: str) -> Exception:
        return Exception(f"[{stage}] {message}")

    async def _login(self, page):
        try:
            await page.goto(
                self.config.orangehrm_url,
                wait_until="domcontentloaded",
                timeout=60000,
            )
        except PlaywrightTimeoutError as exc:
            raise self._build_stage_error("Authorization", f"portal_unreachable: {exc}") from exc
        except Exception as exc:
            raise self._build_stage_error("Authorization", f"portal_network_error: {exc}") from exc

        await page.locator('input[name="username"]').wait_for(timeout=15000)
        await page.locator('input[name="password"]').wait_for(timeout=15000)

        await page.fill('input[name="username"]', self.config.orangehrm_username)
        await page.fill('input[name="password"]', self.config.orangehrm_password)
        await page.click('button[type="submit"]')

        try:
            await page.wait_for_url("**/dashboard/**", timeout=15000)
        except PlaywrightTimeoutError:
            error_box = page.locator(".oxd-alert-content-text")
            error_text = None
            if await error_box.count() > 0:
                error_text = (await error_box.first.text_content() or "").strip()

            if error_text:
                raise self._build_stage_error(
                    "Authorization",
                    f"login_failed: current_url={page.url}; error_text={error_text}",
                )
            raise self._build_stage_error(
                "Authorization",
                f"login_failed: current_url={page.url}",
            )

        await page.wait_for_timeout(1500)

    async def _open_pim_module(self, page):
        await page.get_by_role("link", name="PIM").click()
        await page.wait_for_timeout(2500)

    async def _open_employee_list(self, page):
        await self._open_pim_module(page)
        await page.get_by_role("link", name="Employee List").click()
        await page.wait_for_timeout(2500)

    async def _open_add_employee(self, page):
        await self._open_pim_module(page)
        await page.get_by_role("link", name="Add Employee").click()
        await page.wait_for_timeout(2500)

    async def _clear_employee_search_form(self, page):
        reset_button = page.locator('button[type="reset"]')
        if await reset_button.count() > 0:
            await reset_button.first.click()
            await page.wait_for_timeout(1000)

    async def _search_employee(self, page, first_name: str, last_name: str) -> bool:
        await self._open_employee_list(page)
        await self._clear_employee_search_form(page)

        full_name = f"{first_name} {last_name}"
        name_input = page.locator('input[placeholder="Type for hints..."]').first
        await name_input.fill(full_name)
        await page.wait_for_timeout(1500)

        await page.locator('button[type="submit"]').first.click()
        await page.wait_for_timeout(2500)

        rows = page.locator("div.oxd-table-body .oxd-table-card")
        return await rows.count() > 0

    async def _open_employee_record(self, page, first_name: str, last_name: str):
        found = await self._search_employee(page, first_name, last_name)
        if not found:
            raise self._build_stage_error(
                "Employee Search",
                f"employee_not_found: {first_name} {last_name}",
            )

        first_row = page.locator("div.oxd-table-body .oxd-table-card").first
        await first_row.click()
        await page.wait_for_timeout(3000)

    async def _add_employee(self, page, first_name: str, last_name: str):
        await self._open_add_employee(page)

        await page.fill('input[name="firstName"]', first_name)
        await page.fill('input[name="lastName"]', last_name)

        await page.locator('button[type="submit"]').first.click()
        await page.wait_for_timeout(3500)

    async def _open_job_section(self, page):
        await page.get_by_role("link", name="Job").click()
        await page.wait_for_timeout(2500)
        await page.locator("label", has_text="Job Title").wait_for(timeout=10000)

    async def _get_open_dropdown_options(self, page) -> list[str]:
        options = page.locator('[role="listbox"] [role="option"]')
        count = await options.count()

        values = []
        for i in range(count):
            text = (await options.nth(i).text_content() or "").strip()
            if text:
                values.append(text)
        return values

    async def _select_from_open_listbox(
        self,
        page,
        option_text: str,
        field_name: str,
    ):
        options = await self._get_open_dropdown_options(page)

        if option_text not in options:
            raise self._build_stage_error(
                "Employee Data Update",
                f"{field_name}_not_available: target='{option_text}'",
            )

        await page.get_by_role("option", name=option_text, exact=True).click()
        await page.wait_for_timeout(800)

    async def _open_dropdown_by_label(self, page, label_text: str):
        label = page.locator("label", has_text=label_text).first
        await label.wait_for(timeout=10000)

        field_container = label.locator(
            "xpath=ancestor::div[contains(@class, 'oxd-input-group')]"
        ).first
        dropdown = field_container.locator(".oxd-select-text").first

        if await dropdown.count() == 0:
            raise self._build_stage_error(
                "Employee Data Update",
                f"{label_text}_dropdown_not_found",
            )

        await dropdown.click()
        await page.wait_for_timeout(800)

    async def _set_job_details(self, page, job_title: str, employment_status: str):
        await self._open_job_section(page)

        await self._open_dropdown_by_label(page, "Job Title")
        await self._select_from_open_listbox(
            page=page,
            option_text=job_title,
            field_name="job_title",
        )

        await self._open_dropdown_by_label(page, "Employment Status")
        await self._select_from_open_listbox(
            page=page,
            option_text=employment_status,
            field_name="employment_status",
        )

        save_buttons = page.locator('button[type="submit"]')
        if await save_buttons.count() == 0:
            raise self._build_stage_error(
                "Employee Data Update",
                "job_details_save_button_not_found",
            )

        await save_buttons.first.click()
        await page.wait_for_timeout(2500)

    async def _open_salary_section(self, page):
        salary_link = page.get_by_role("link", name="Salary")
        await salary_link.wait_for(timeout=10000)
        await salary_link.click()
        await page.wait_for_timeout(2500)

    async def _salary_attachment_exists(self, page, first_name: str, last_name: str) -> bool:
        await self._open_salary_section(page)

        expected_name_part = f"{first_name}_{last_name}_salary"
        body_text = (await page.locator("body").text_content() or "").strip()
        return expected_name_part in body_text

    def _build_salary_file(self, item: dict) -> tuple[str, str]:
        filename = f"{item['first_name']}_{item['last_name']}_salary.txt"
        content = item["salary_text"]

        temp_dir = Path(tempfile.gettempdir())
        file_path = temp_dir / filename
        file_path.write_text(content, encoding="utf-8")

        return str(file_path), filename

    async def _upload_salary_attachment_if_missing(self, page, item: dict) -> bool:
        exists = await self._salary_attachment_exists(
            page,
            item["first_name"],
            item["last_name"],
        )
        if exists:
            return False

        add_buttons = page.get_by_role("button", name="Add")
        add_count = await add_buttons.count()

        if add_count == 0:
            raise self._build_stage_error(
                "Salary Attachment Upload",
                "salary_add_button_not_found",
            )

        salary_add_button = add_buttons.nth(add_count - 1)
        await salary_add_button.wait_for(timeout=10000)
        await salary_add_button.click()
        await page.wait_for_timeout(1500)

        file_path, filename = self._build_salary_file(item)

        file_input = page.locator('input[type="file"]')
        input_count = await file_input.count()
        if input_count == 0:
            raise self._build_stage_error(
                "Salary Attachment Upload",
                "attachment_file_input_not_found",
            )

        await file_input.nth(input_count - 1).set_input_files(file_path)

        comment = page.locator("textarea")
        comment_count = await comment.count()
        if comment_count > 0:
            await comment.nth(comment_count - 1).fill(
                f"Salary attachment uploaded by automation: {filename}"
            )

        save_buttons = page.locator('button[type="submit"]')
        save_count = await save_buttons.count()
        if save_count == 0:
            raise self._build_stage_error(
                "Salary Attachment Upload",
                "salary_attachment_save_button_not_found",
            )

        await save_buttons.nth(save_count - 1).click()
        await page.wait_for_timeout(2500)

        return True

    async def process_item(self, item: dict):
        async with BrowserSession() as page:
            first_name = item["first_name"]
            last_name = item["last_name"]

            try:
                await self._login(page)

                exists_before = await self._search_employee(page, first_name, last_name)
                created = False

                if not exists_before:
                    await self._add_employee(page, first_name, last_name)
                    created = True

                await self._open_employee_record(page, first_name, last_name)

                await self._set_job_details(
                    page=page,
                    job_title=item["job_title"],
                    employment_status=item["employment_status"],
                )

                salary_uploaded = await self._upload_salary_attachment_if_missing(page, item)

                return {
                    "first_name": first_name,
                    "last_name": last_name,
                    "item_label": f"{first_name} {last_name}",
                    "detail_stage": "Completed",
                    "job_title": item["job_title"],
                    "employment_status": item["employment_status"],
                    "salary_text": item["salary_text"],
                    "created": created,
                    "exists_before": exists_before,
                    "exists_after": True,
                    "salary_uploaded": salary_uploaded,
                }
            except Exception as exc:
                raise self._build_stage_error(
                    "Employee Processing",
                    f"item_label={first_name} {last_name}; {exc}",
                ) from exc