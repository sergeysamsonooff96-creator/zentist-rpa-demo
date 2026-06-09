from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from src.app.core.base_runner import BasePortalRunnerZX
from src.app.core.browser import BrowserSession
from src.app.core.retry import ui_retry, RetryableUiError
from src.app.portals.saucedemo.data import SAUCE_USERS


class SauceDemoRunner(BasePortalRunnerZX):
    @property
    def portal_name(self) -> str:
        return "saucedemo"

    def iter_items(self):
        return SAUCE_USERS

    def _build_stage_error(self, stage: str, message: str) -> Exception:
        return Exception(f"[{stage}] {message}")

    @ui_retry()
    async def _open_login_page(self, page):
        try:
            await page.goto(
                self.config.saucedemo_url,
                wait_until="domcontentloaded",
                timeout=60000,
            )
        except PlaywrightTimeoutError as exc:
            raise RetryableUiError(f"saucedemo_unreachable_timeout: {exc}") from exc
        except Exception as exc:
            raise RetryableUiError(f"saucedemo_network_error: {exc}") from exc

        await page.locator('[data-test="username"]').wait_for(timeout=15000)
        await page.locator('[data-test="password"]').wait_for(timeout=15000)

    async def _login(self, page, username: str):
        await self._open_login_page(page)

        await page.fill('[data-test="username"]', username)
        await page.fill('[data-test="password"]', self.config.saucedemo_password)
        await page.click('[data-test="login-button"]')

        await page.wait_for_timeout(1500)

        if "inventory" in page.url:
            return

        error_box = page.locator('[data-test="error"]')
        error_text = None
        if await error_box.count() > 0:
            error_text = (await error_box.first.text_content() or "").strip()

        if error_text:
            raise self._build_stage_error("Authorization", f"login_failed: {error_text}")
        raise self._build_stage_error("Authorization", "login_failed_without_visible_error")

    @ui_retry()
    async def _add_product(self, page, product_name: str):
        product_card = page.locator(".inventory_item").filter(has_text=product_name).first
        await product_card.wait_for(timeout=10000)

        button = product_card.locator("button").first
        await button.wait_for(timeout=5000)

        button_text = (await button.text_content() or "").strip()
        if "Add to cart" not in button_text:
            raise RetryableUiError(f"add_to_cart_button_not_ready: {product_name}")

        await button.click()
        await page.wait_for_timeout(600)

    async def _add_products(self, page, item_names: list[str]) -> list[str]:
        added_items = []

        for product_name in item_names:
            try:
                await self._add_product(page, product_name)
                added_items.append(product_name)
            except Exception as exc:
                raise self._build_stage_error(
                    "Cart Update",
                    f"failed_to_add_product: {product_name}; {exc}",
                ) from exc

        cart_badge = page.locator(".shopping_cart_badge")
        await cart_badge.wait_for(timeout=5000)
        cart_count = (await cart_badge.text_content() or "").strip()

        if cart_count != str(len(item_names)):
            raise self._build_stage_error(
                "Cart Update",
                f"cart_count_mismatch: expected={len(item_names)} actual={cart_count}",
            )

        return added_items

    async def _checkout(self, page) -> tuple[str, str, str]:
        try:
            await page.click(".shopping_cart_link")
            await page.wait_for_timeout(1000)

            await page.click('[data-test="checkout"]')
            await page.wait_for_timeout(1000)

            await page.fill('[data-test="firstName"]', "Sam")
            await page.fill('[data-test="lastName"]', "Test")
            await page.fill('[data-test="postalCode"]', "420000")
            await page.click('[data-test="continue"]')
            await page.wait_for_timeout(1200)
        except Exception as exc:
            raise self._build_stage_error("Checkout", f"checkout_step_failed: {exc}") from exc

        try:
            payment_info = (await page.locator('[data-test="payment-info-value"]').text_content() or "").strip()
            shipping_info = (await page.locator('[data-test="shipping-info-value"]').text_content() or "").strip()
            total_text = (await page.locator('[data-test="total-label"]').text_content() or "").strip()
        except Exception as exc:
            raise self._build_stage_error("Checkout", f"checkout_summary_read_failed: {exc}") from exc

        return payment_info, shipping_info, total_text

    async def _finish_order(self, page) -> tuple[str, str]:
        try:
            await page.click('[data-test="finish"]')
            await page.wait_for_timeout(1500)
        except Exception as exc:
            raise self._build_stage_error("Order Completion", f"finish_click_failed: {exc}") from exc

        if "checkout-complete" not in page.url:
            raise self._build_stage_error(
                "Order Completion",
                f"checkout_complete_not_reached: current_url={page.url}",
            )

        complete_header = (await page.locator('[data-test="complete-header"]').text_content() or "").strip()
        complete_text = (await page.locator('[data-test="complete-text"]').text_content() or "").strip()

        return complete_header, complete_text

    async def process_item(self, item):
        async with BrowserSession() as page:
            username = item

            try:
                await self._login(page, username)

                item_names = [
                    "Sauce Labs Backpack",
                    "Sauce Labs Bike Light",
                    "Sauce Labs Bolt T-Shirt",
                ]

                added_items = await self._add_products(page, item_names)

                payment_info, shipping_info, total_text = await self._checkout(page)
                complete_header, complete_text = await self._finish_order(page)

                return {
                    "account": username,
                    "item_label": username,
                    "detail_stage": "Completed",
                    "order_status": "completed",
                    "items_added": added_items,
                    "item_count": len(added_items),
                    "payment_info": payment_info,
                    "shipping_info": shipping_info,
                    "total": total_text,
                    "complete_header": complete_header,
                    "complete_text": complete_text,
                    "final_url": page.url,
                }
            except Exception as exc:
                raise self._build_stage_error(
                    "Account Processing",
                    f"item_label={username}; {exc}",
                ) from exc