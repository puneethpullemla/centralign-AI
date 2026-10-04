import logging
from typing import Dict, Any, Optional
from playwright.async_api import Page
from app.config import settings

logger = logging.getLogger(__name__)


class BillingTools:
    """Tools for interacting with the simulated Internal Billing System."""

    @staticmethod
    async def open_portal(page: Page, fail_once: bool = False, target_url: Optional[str] = None) -> Dict[str, Any]:
        url = target_url or settings.BILLING_PORTAL_URL
        if fail_once:
            url += ("&" if "?" in url else "?") + "fail_once=true"

        logger.info(f"Navigating to Billing Portal: {url}")
        await page.goto(url, wait_until="networkidle")
        title = await page.title()
        return {
            "action": "open_billing_portal",
            "url": page.url,
            "title": title,
            "status": "success",
            "observation": f"Opened Internal Billing System at {page.url}."
        }

    @staticmethod
    async def fill_billing_form(
        page: Page,
        company: str,
        invoice_id: str,
        amount: str,
        due_date: str
    ) -> Dict[str, Any]:
        logger.info(f"Filling billing form: {company}, {invoice_id}, {amount}, {due_date}")
        await page.click("#tab-create")
        await page.wait_for_selector("#company-input", state="visible", timeout=5000)

        await page.fill("#company-input", company)
        await page.fill("#invoice-id-input", invoice_id)
        await page.fill("#amount-input", amount)
        await page.fill("#due-date-input", due_date)

        return {
            "action": "fill_billing_form",
            "company": company,
            "invoice_id": invoice_id,
            "amount": amount,
            "due_date": due_date,
            "status": "success",
            "observation": f"Populated billing form with Invoice: {invoice_id}, Company: {company}, Amount: {amount}, Due Date: {due_date}."
        }

    @staticmethod
    async def submit_billing_record(
        page: Page,
        expected_data: Optional[Dict[str, Any]] = None,
        fail_once: bool = False
    ) -> Dict[str, Any]:
        """Submits billing form deterministically with pre-submission verification and diagnostics."""
        logger.info("Submitting billing record form")

        # 1. Ensure page is at the billing portal
        if "billing-portal" not in page.url:
            logger.info(f"Page is not on billing portal (url={page.url}). Navigating to portal.")
            await BillingTools.open_portal(page, fail_once=fail_once)

        create_tab = page.locator("#tab-create")
        panel_create = page.locator("#panel-create")
        save_btn = page.locator("#save-record-button")

        # 2. Log comprehensive UI diagnostics
        tab_create_vis = await create_tab.is_visible()
        panel_create_vis = await panel_create.is_visible()
        save_vis = await save_btn.is_visible()
        save_en = await save_btn.is_enabled() if save_vis else False

        logger.info(
            "Billing UI state: url=%s create_tab_visible=%s "
            "create_panel_visible=%s save_visible=%s save_enabled=%s",
            page.url,
            tab_create_vis,
            panel_create_vis,
            save_vis,
            save_en,
        )

        # 3. Ensure Create tab and panel are active and visible
        if not await panel_create.is_visible():
            logger.info("Create panel is hidden. Switching to Create tab...")
            await create_tab.wait_for(state="visible", timeout=5000)
            await create_tab.click()
            await panel_create.wait_for(state="visible", timeout=5000)

        # 4. Verify and restore form fields from agent state if needed
        if expected_data:
            company = expected_data.get("company", "")
            invoice_id = expected_data.get("invoice_id", "")
            amount = expected_data.get("amount", "")
            due_date = expected_data.get("due_date", "")

            curr_company = (await page.locator("#company-input").input_value()).strip()
            curr_invoice = (await page.locator("#invoice-id-input").input_value()).strip()
            curr_amount = (await page.locator("#amount-input").input_value()).strip()
            curr_due_date = (await page.locator("#due-date-input").input_value()).strip()

            if (not curr_company or curr_company != company) and company:
                logger.info(f"Restoring company field: {company}")
                await page.fill("#company-input", company)
            if (not curr_invoice or curr_invoice != invoice_id) and invoice_id:
                logger.info(f"Restoring invoice_id field: {invoice_id}")
                await page.fill("#invoice-id-input", invoice_id)
            if (not curr_amount or curr_amount != amount) and amount:
                logger.info(f"Restoring amount field: {amount}")
                await page.fill("#amount-input", amount)
            if (not curr_due_date or curr_due_date != due_date) and due_date:
                logger.info(f"Restoring due_date field: {due_date}")
                await page.fill("#due-date-input", due_date)

        # 5. Stable wait for Save button visibility and enabled state
        try:
            await save_btn.wait_for(state="visible", timeout=5000)
        except Exception as e:
            logger.error(f"Save button did not become visible: {e}")
            return {
                "action": "submit_billing_record",
                "status": "failed",
                "recoverable": True,
                "error": f"Save button (#save-record-button) is not visible: {e}",
                "url": page.url,
                "panel_create_visible": await panel_create.is_visible()
            }

        if not await save_btn.is_enabled():
            logger.error("Save button is disabled.")
            return {
                "action": "submit_billing_record",
                "status": "failed",
                "recoverable": True,
                "error": "Save button (#save-record-button) is disabled.",
                "url": page.url
            }

        # 6. Click Save
        await save_btn.click()

        # 7. Wait for either success or error response
        success_banner = page.locator("#success-banner")
        error_banner = page.locator("#error-banner")

        try:
            await page.wait_for_function(
                """() => {
                    const success = document.querySelector('#success-banner');
                    const error = document.querySelector('#error-banner');

                    const successVisible =
                        success && getComputedStyle(success).display !== 'none';

                    const errorVisible =
                        error && getComputedStyle(error).display !== 'none';

                    return successVisible || errorVisible;
                }""",
                timeout=5000
            )
        except Exception:
            logger.error("Neither success nor error banner appeared after saving.")

            return {
                "action": "submit_billing_record",
                "status": "failed",
                "recoverable": True,
                "error": "Billing portal did not return a success or error response after Save.",
                "url": page.url
            }

        # 8. Check error first
        if await error_banner.is_visible():
            err_msg = await page.locator("#error-message").text_content()
            err_text = err_msg.strip() if err_msg else "Save operation failed."

            logger.warning(f"Billing save operation failed: {err_text}")

            return {
                "action": "submit_billing_record",
                "status": "failed",
                "recoverable": True,
                "error": err_text,
                "observation": f"Billing portal reported error: {err_text}"
            }

        # 9. Check success
        if await success_banner.is_visible():
            record_id_text = await page.locator("#created-record-id").text_content()
            record_id = record_id_text.strip() if record_id_text else "UNKNOWN"

            logger.info(f"Billing record created successfully: {record_id}")

            return {
                "action": "submit_billing_record",
                "status": "success",
                "record_id": record_id,
                "observation": (
                    f"Billing record saved successfully with generated "
                    f"Record ID: {record_id}."
                )
            }