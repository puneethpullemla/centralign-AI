import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from playwright.async_api import Page

from app.config import settings

logger = logging.getLogger(__name__)


class InvoiceTools:
    """Tools for interacting with the simulated Invoice Portal."""

    @staticmethod
    async def open_portal(
        page: Page,
        fail_once: bool = False,
        target_url: Optional[str] = None,
    ) -> Dict[str, Any]:

        url = target_url or settings.INVOICE_PORTAL_URL

        if fail_once:
            url += ("&" if "?" in url else "?") + "fail_once=true"

        logger.info(f"Navigating to Invoice Portal: {url}")

        await page.goto(url, wait_until="networkidle")

        return {
            "action": "open_invoice_portal",
            "status": "success",
            "url": page.url,
            "title": await page.title(),
            "observation": f"Opened Invoice Portal at {page.url}.",
        }

    @staticmethod
    async def search_company(
        page: Page,
        company: str,
    ) -> Dict[str, Any]:

        logger.info(
            f"Searching invoice portal for company: {company}"
        )

        if "invoice-portal" not in page.url:
            await InvoiceTools.open_portal(page)

        # Wait for the invoice table itself.
        tbody = page.locator("#invoices-tbody")

        try:
            await tbody.wait_for(
                state="attached",
                timeout=5000,
            )
        except Exception as e:
            return {
                "action": "search_company_invoices",
                "status": "failed",
                "recoverable": False,
                "error": (
                    f"Invoice portal table could not be loaded: {str(e)}"
                ),
                "observation": "Invoice table was not available.",
            }

        rows = page.locator("#invoices-tbody tr")

        invoices: List[Dict[str, Any]] = []

        row_count = await rows.count()

        for i in range(row_count):
            row = rows.nth(i)

            try:
                invoice_id_el = row.locator(".invoice-id")
                company_el = row.locator(".company")
                date_el = row.locator(".invoice-date")
                amount_el = row.locator(".amount")
                due_date_el = row.locator(".due-date")

                if await invoice_id_el.count() == 0:
                    continue

                invoice_id = await invoice_id_el.text_content()
                row_company = (
                    await company_el.text_content()
                    if await company_el.count()
                    else ""
                )
                invoice_date = (
                    await date_el.text_content()
                    if await date_el.count()
                    else ""
                )
                amount = (
                    await amount_el.text_content()
                    if await amount_el.count()
                    else ""
                )
                due_date = (
                    await due_date_el.text_content()
                    if await due_date_el.count()
                    else ""
                )

                invoice_id = (invoice_id or "").strip()
                row_company = (row_company or "").strip()
                invoice_date = (invoice_date or "").strip()
                amount = (amount or "").strip()
                due_date = (due_date or "").strip()

                if not invoice_id:
                    continue

                # Match company case-insensitively.
                if row_company.lower() != company.strip().lower():
                    continue

                invoices.append({
                    "invoice_id": invoice_id,
                    "company": row_company,
                    "date": invoice_date,
                    "amount": amount,
                    "due_date": due_date,
                })

            except Exception as e:
                logger.warning(
                    f"Could not parse invoice row {i}: {e}"
                )

        invoice_count = len(invoices)

        if invoice_count == 0:
            error_message = (
                f"No invoices found for company '{company}'."
            )

            logger.warning(error_message)

            return {
                "action": "search_company_invoices",
                "status": "failed",
                "recoverable": False,
                "business_error": True,
                "company": company,
                "invoices": [],
                "invoice_count": 0,
                "count": 0,
                "found": False,
                "error": error_message,
                "observation": error_message,
            }

        logger.info(
            f"Found {invoice_count} invoice(s) "
            f"for company '{company}'."
        )

        return {
            "action": "search_company_invoices",
            "status": "success",
            "company": company,
            "invoices": invoices,
            "invoice_count": invoice_count,
            "count": invoice_count,
            "found": True,
            "observation": (
                f"Found {invoice_count} invoice(s) "
                f"matching '{company}'."
            ),
        }

    @staticmethod
    async def extract_latest_invoice(
        page: Page,
        company: Optional[str] = None,
    ) -> Dict[str, Any]:

        logger.info(
            f"Extracting latest invoice"
            + (f" for {company}" if company else "")
        )

        tbody = page.locator("#invoices-tbody")

        try:
            await tbody.wait_for(
                state="attached",
                timeout=5000,
            )
        except Exception as e:
            return {
                "action": "extract_latest_invoice",
                "status": "failed",
                "recoverable": False,
                "error": str(e),
                "observation": "Invoice table was not available.",
            }

        rows = page.locator("#invoices-tbody tr")

        invoices: List[Dict[str, Any]] = []

        for i in range(await rows.count()):

            row = rows.nth(i)

            try:
                invoice_id_el = row.locator(".invoice-id")

                if await invoice_id_el.count() == 0:
                    continue

                invoice_id = await invoice_id_el.text_content()

                company_el = row.locator(".company")
                date_el = row.locator(".invoice-date")
                amount_el = row.locator(".amount")
                due_date_el = row.locator(".due-date")

                row_company = (
                    await company_el.text_content()
                    if await company_el.count()
                    else ""
                )

                invoice_date = (
                    await date_el.text_content()
                    if await date_el.count()
                    else ""
                )

                amount = (
                    await amount_el.text_content()
                    if await amount_el.count()
                    else ""
                )

                due_date = (
                    await due_date_el.text_content()
                    if await due_date_el.count()
                    else ""
                )

                invoice_id = (invoice_id or "").strip()
                row_company = (row_company or "").strip()
                invoice_date = (invoice_date or "").strip()
                amount = (amount or "").strip()
                due_date = (due_date or "").strip()

                if not invoice_id:
                    continue

                if (
                    company
                    and row_company.lower() != company.lower()
                ):
                    continue

                invoices.append({
                    "invoice_id": invoice_id,
                    "company": row_company or company or "",
                    "date": invoice_date,
                    "amount": amount,
                    "due_date": due_date,
                })

            except Exception as e:
                logger.warning(
                    f"Could not parse invoice row {i}: {e}"
                )

        if not invoices:
            company_name = company or "requested company"

            error_message = (
                f"No invoices found for company '{company_name}'."
            )

            return {
                "action": "extract_latest_invoice",
                "status": "failed",
                "recoverable": False,
                "business_error": True,
                "invoice_count": 0,
                "error": error_message,
                "observation": error_message,
            }

        def parse_date(invoice: Dict[str, Any]):
            date_value = invoice.get("date", "")

            formats = [
                "%Y-%m-%d",
                "%d-%m-%Y",
                "%d/%m/%Y",
                "%Y/%m/%d",
                "%m/%d/%Y",
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(
                        date_value,
                        fmt,
                    )
                except ValueError:
                    continue

            return datetime.min

        invoices.sort(
            key=parse_date,
            reverse=True,
        )

        latest = invoices[0]

        logger.info(
            f"Latest invoice identified: "
            f"{latest['invoice_id']}"
        )

        return {
            "action": "extract_latest_invoice",
            "status": "success",
            "invoice_count": len(invoices),
            "latest_invoice": latest,
            "observation": (
                f"Identified latest invoice "
                f"'{latest['invoice_id']}' for "
                f"{latest['company']} dated "
                f"{latest['date']} with Amount: "
                f"{latest['amount']} and Due Date: "
                f"{latest['due_date']}."
            ),
        }