import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from playwright.async_api import Page
from app.config import settings

logger = logging.getLogger(__name__)


class InvoiceTools:
    """Tools for interacting with the simulated Invoice Portal."""

    @staticmethod
    async def open_portal(page: Page, target_url: Optional[str] = None) -> Dict[str, Any]:
        url = target_url or settings.INVOICE_PORTAL_URL
        logger.info(f"Navigating to Invoice Portal: {url}")
        await page.goto(url, wait_until="networkidle")
        title = await page.title()
        return {
            "action": "open_portal",
            "url": page.url,
            "title": title,
            "status": "success",
            "observation": f"Opened Invoice Portal at {page.url}."
        }

    @staticmethod
    async def search_company(page: Page, company_name: str) -> Dict[str, Any]:
        logger.info(f"Searching invoice portal for company: {company_name}")
        await page.wait_for_selector("#search-input", state="visible", timeout=5000)
        await page.fill("#search-input", company_name)
        await page.click("#search-button")
        await page.wait_for_timeout(300)

        # Check search status text
        status_text = await page.locator("#search-status").text_content()
        return {
            "action": "search_company",
            "company": company_name,
            "status": "success",
            "observation": f"Filtered invoices by company '{company_name}'. UI status: {status_text}"
        }

    @staticmethod
    async def extract_latest_invoice(page: Page, company_name: Optional[str] = None) -> Dict[str, Any]:
        """Extracts visible invoices, determines the latest by date, and returns details."""
        logger.info(f"Extracting invoices from table for company: {company_name}")
        await page.wait_for_selector("#invoices-tbody", state="visible", timeout=5000)

        rows = await page.locator("#invoices-tbody tr.invoice-row").all()
        invoices: List[Dict[str, Any]] = []

        for row in rows:
            inv_id = await row.locator(".invoice-id").text_content()
            comp = await row.locator(".company-name").text_content()
            date_str = await row.locator(".invoice-date").text_content()
            amt = await row.locator(".invoice-amount").text_content()
            due = await row.locator(".invoice-due-date").text_content()

            inv_data = {
                "invoice_id": inv_id.strip() if inv_id else "",
                "company": comp.strip() if comp else "",
                "date": date_str.strip() if date_str else "",
                "amount": amt.strip() if amt else "",
                "due_date": due.strip() if due else ""
            }

            # Filter by company if requested
            if company_name:
                if company_name.lower() in inv_data["company"].lower():
                    invoices.append(inv_data)
            else:
                invoices.append(inv_data)

        if not invoices:
            raise ValueError(f"No invoices found on page for company '{company_name or 'any'}'.")

        # Sort dynamically by parsed date descending to find the latest invoice
        def parse_date(d: str):
            try:
                return datetime.strptime(d, "%Y-%m-%d")
            except Exception:
                return datetime.min

        sorted_invoices = sorted(invoices, key=lambda x: parse_date(x["date"]), reverse=True)
        latest = sorted_invoices[0]

        logger.info(f"Identified latest invoice dynamically: {latest['invoice_id']} dated {latest['date']}")
        return {
            "action": "extract_latest_invoice",
            "status": "success",
            "latest_invoice": latest,
            "total_found": len(invoices),
            "observation": (
                f"Identified latest invoice '{latest['invoice_id']}' for {latest['company']} "
                f"dated {latest['date']} with Amount: {latest['amount']} and Due Date: {latest['due_date']}."
            )
        }
