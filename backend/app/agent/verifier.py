import logging
import re
from typing import Dict, Any, Tuple
from app.tools.billing_tools import BillingTools
from app.tools.browser import BrowserManager

logger = logging.getLogger(__name__)


def normalize_amount(val: Any) -> str:
    """Extracts numeric digits to safely compare currencies across encodings."""
    if not val:
        return ""
    # Strip everything except digits and decimal point
    digits = re.sub(r"[^\d]", "", str(val))
    return digits


class Verifier:
    """Performs independent verification of committed records against source invoice data."""

    @staticmethod
    async def verify_record(
        browser_manager: BrowserManager,
        source_data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], str]:
        """
        Navigates to billing records search, queries by invoice ID, and validates every attribute.
        Returns: (verification_result_dict, screenshot_path)
        """
        page = await browser_manager.get_page()
        invoice_id = source_data.get("invoice_id", "").strip()
        target_company = source_data.get("company", "").strip()
        target_amount = source_data.get("amount", "")
        target_due_date = source_data.get("due_date", "").strip()

        logger.info(f"Initiating independent verification for Invoice ID: {invoice_id}")

        # Execute search in ledger
        search_result = await BillingTools.search_billing_record(page, invoice_id)

        # Capture verification screenshot
        screenshot_path, _ = await browser_manager.capture_screenshot(
            f"verification_{invoice_id}",
            description=f"Independent ledger verification for {invoice_id}"
        )

        if not search_result.get("found") or not search_result.get("record"):
            logger.warning(f"Verification failed: Invoice {invoice_id} not found in billing ledger.")
            return {
                "verified": False,
                "reason": f"No ledger record found matching invoice ID {invoice_id}.",
                "invoice_id": invoice_id,
                "company_matches": False,
                "amount_matches": False,
                "due_date_matches": False,
                "record_id": None
            }, screenshot_path

        found_record = search_result["record"]

        # Validate matching fields
        company_matches = target_company.lower() in found_record.get("company", "").lower()
        amount_matches = normalize_amount(target_amount) == normalize_amount(found_record.get("amount", ""))
        due_date_matches = target_due_date == found_record.get("due_date", "").strip()

        all_matched = company_matches and amount_matches and due_date_matches

        verification_result = {
            "verified": all_matched,
            "record_id": found_record.get("record_id"),
            "invoice_id": invoice_id,
            "company_matches": company_matches,
            "amount_matches": amount_matches,
            "due_date_matches": due_date_matches,
            "source_data": {
                "company": target_company,
                "amount": target_amount,
                "due_date": target_due_date
            },
            "ledger_data": found_record
        }

        if all_matched:
            logger.info(f"Verification SUCCESS: Record {found_record.get('record_id')} matches invoice {invoice_id}.")
        else:
            logger.error(
                f"Verification MISMATCH: Source and ledger records do not match. "
                f"Company match={company_matches}, Amount match={amount_matches}, Due Date match={due_date_matches}. "
                f"Result: {verification_result}"
            )

        return verification_result, screenshot_path
