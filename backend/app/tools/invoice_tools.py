import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from playwright.async_api import Page

from app.config import settings

logger = logging.getLogger(__name__)


class InvoiceTools:
    """Tools for interacting with the simulated Invoice Portal."""

    # ============================================================
    # OPEN INVOICE PORTAL
    # ============================================================

    @staticmethod
    async def open_portal(
        page: Page,
        fail_once: bool = False,
        target_url: Optional[str] = None,
    ) -> Dict[str, Any]:

        url = target_url or settings.INVOICE_PORTAL_URL

        if fail_once:
            url += (
                ("&" if "?" in url else "?")
                + "fail_once=true"
            )

        logger.info(
            f"Navigating to Invoice Portal: {url}"
        )

        await page.goto(
            url,
            wait_until="networkidle",
        )

        title = await page.title()

        return {
            "action": "open_invoice_portal",
            "status": "success",
            "url": page.url,
            "title": title,
            "observation": (
                f"Opened Invoice Portal at {page.url}."
            ),
        }

    # ============================================================
    # SEARCH COMPANY INVOICES
    # ============================================================

    @staticmethod
    async def search_company(
        page: Page,
        company: str,
    ) -> Dict[str, Any]:

        logger.info(
            f"Searching invoice portal for company: {company}"
        )

        # --------------------------------------------------------
        # Make sure we are on invoice portal
        # --------------------------------------------------------

        if "invoice-portal" not in page.url:

            await InvoiceTools.open_portal(page)

        # --------------------------------------------------------
        # Locate company search field
        # --------------------------------------------------------

        search_input = page.locator(
            "#company-search"
        )

        await search_input.wait_for(
            state="visible",
            timeout=5000,
        )

        # --------------------------------------------------------
        # Search company
        # --------------------------------------------------------

        await search_input.fill(company)

        # Click search if the button exists
        search_button = page.locator(
            "#search-button"
        )

        if await search_button.count() > 0:

            await search_button.click()

        else:

            # Some versions of the portal filter
            # automatically after typing.
            await page.keyboard.press("Enter")

        # --------------------------------------------------------
        # Give the UI time to update
        # --------------------------------------------------------

        await page.wait_for_timeout(300)

        # --------------------------------------------------------
        # IMPORTANT:
        # Do NOT wait for invoices-tbody to be "visible".
        #
        # The tbody itself can technically be hidden while
        # the rows/table are rendered.
        # --------------------------------------------------------

        tbody = page.locator(
            "#invoices-tbody"
        )

        await tbody.wait_for(
            state="attached",
            timeout=5000,
        )

        # --------------------------------------------------------
        # Read invoice rows
        # --------------------------------------------------------

        rows = page.locator(
            "#invoices-tbody tr"
        )

        row_count = await rows.count()

        invoices: List[Dict[str, Any]] = []

        for i in range(row_count):

            row = rows.nth(i)

            # Ignore empty/non-invoice rows
            if await row.locator(
                ".invoice-row"
            ).count() == 0:

                # If the portal does not use
                # .invoice-row, continue processing.
                pass

            try:

                invoice_id_el = row.locator(
                    ".invoice-id"
                )

                company_el = row.locator(
                    ".company"
                )

                date_el = row.locator(
                    ".invoice-date"
                )

                amount_el = row.locator(
                    ".amount"
                )

                due_date_el = row.locator(
                    ".due-date"
                )

                invoice_id = (
                    await invoice_id_el.text_content()
                    if await invoice_id_el.count()
                    else ""
                )

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

                invoice_id = (
                    invoice_id.strip()
                    if invoice_id
                    else ""
                )

                row_company = (
                    row_company.strip()
                    if row_company
                    else ""
                )

                invoice_date = (
                    invoice_date.strip()
                    if invoice_date
                    else ""
                )

                amount = (
                    amount.strip()
                    if amount
                    else ""
                )

                due_date = (
                    due_date.strip()
                    if due_date
                    else ""
                )

                # ------------------------------------------------
                # Only include actual invoice records
                # ------------------------------------------------

                if not invoice_id:
                    continue

                # ------------------------------------------------
                # If company is available in the row,
                # verify it matches the requested company.
                # ------------------------------------------------

                if row_company:

                    if (
                        row_company.lower().strip()
                        != company.lower().strip()
                    ):
                        continue

                invoices.append(
                    {
                        "invoice_id": invoice_id,
                        "company": (
                            row_company or company
                        ),
                        "date": invoice_date,
                        "amount": amount,
                        "due_date": due_date,
                    }
                )

            except Exception as e:

                logger.warning(
                    f"Could not parse invoice row {i}: {e}"
                )

        # --------------------------------------------------------
        # IMPORTANT BUSINESS RESULT
        # --------------------------------------------------------

        invoice_count = len(invoices)

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
            "found": invoice_count > 0,
            "observation": (
                f"Filtered invoices by company "
                f"'{company}'. UI status: "
                f"Found {invoice_count} invoice(s) "
                f'matching "{company}".'
            ),
        }

    # ============================================================
    # EXTRACT LATEST INVOICE
    # ============================================================

    @staticmethod
    async def extract_latest_invoice(
        page: Page,
        company: Optional[str] = None,
    ) -> Dict[str, Any]:

        logger.info(
            f"Extracting latest invoice"
            + (
                f" for {company}"
                if company
                else ""
            )
        )

        # --------------------------------------------------------
        # Make sure invoice table exists
        # --------------------------------------------------------

        tbody = page.locator(
            "#invoices-tbody"
        )

        await tbody.wait_for(
            state="attached",
            timeout=5000,
        )

        rows = page.locator(
            "#invoices-tbody tr"
        )

        row_count = await rows.count()

        invoices: List[Dict[str, Any]] = []

        for i in range(row_count):

            row = rows.nth(i)

            try:

                invoice_id_el = row.locator(
                    ".invoice-id"
                )

                if await invoice_id_el.count() == 0:
                    continue

                invoice_id = await (
                    invoice_id_el.text_content()
                )

                company_el = row.locator(
                    ".company"
                )

                date_el = row.locator(
                    ".invoice-date"
                )

                amount_el = row.locator(
                    ".amount"
                )

                due_date_el = row.locator(
                    ".due-date"
                )

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

                invoice_id = (
                    invoice_id.strip()
                    if invoice_id
                    else ""
                )

                row_company = (
                    row_company.strip()
                    if row_company
                    else ""
                )

                invoice_date = (
                    invoice_date.strip()
                    if invoice_date
                    else ""
                )

                amount = (
                    amount.strip()
                    if amount
                    else ""
                )

                due_date = (
                    due_date.strip()
                    if due_date
                    else ""
                )

                if not invoice_id:
                    continue

                # ------------------------------------------------
                # Company filter
                # ------------------------------------------------

                if (
                    company
                    and row_company
                    and row_company.lower()
                    != company.lower()
                ):
                    continue

                invoices.append(
                    {
                        "invoice_id": invoice_id,
                        "company": (
                            row_company
                            or company
                            or ""
                        ),
                        "date": invoice_date,
                        "amount": amount,
                        "due_date": due_date,
                    }
                )

            except Exception as e:

                logger.warning(
                    f"Could not parse invoice row {i}: {e}"
                )

        # --------------------------------------------------------
        # No invoice found
        # --------------------------------------------------------

        if not invoices:

            company_name = (
                company
                or "requested company"
            )

            error_message = (
                f"No invoices found for "
                f"company '{company_name}'."
            )

            logger.warning(
                error_message
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

        # --------------------------------------------------------
        # Sort by invoice date
        # --------------------------------------------------------

        def parse_date(invoice: Dict[str, Any]):

            date_value = invoice.get(
                "date",
                "",
            )

            if not date_value:
                return datetime.min

            # Try common formats
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

            # If date cannot be parsed,
            # keep it at the bottom.
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
                f"'{latest['invoice_id']}' "
                f"for {latest.get('company', company)} "
                f"dated {latest.get('date')} "
                f"with Amount: {latest.get('amount')} "
                f"and Due Date: "
                f"{latest.get('due_date')}."
            ),
        }