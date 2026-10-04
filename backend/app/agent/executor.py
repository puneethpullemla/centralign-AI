import logging
from typing import Dict, Any, Tuple
from app.agent.state import AgentState
from app.tools.browser import BrowserManager
from app.tools.invoice_tools import InvoiceTools
from app.tools.billing_tools import BillingTools
from app.agent.verifier import Verifier
from app.agent.observer import Observer

logger = logging.getLogger(__name__)

# Registered valid actions for safety
REGISTERED_ACTIONS = {
    "open_invoice_portal",
    "search_company_invoices",
    "extract_latest_invoice",
    "open_billing_portal",
    "fill_billing_form",
    "submit_billing_record",
    "verify_billing_record"
}


class ToolExecutor:
    """Safely executes registered browser tools and captures observations."""

    @staticmethod
    async def execute_action(
        browser_manager: BrowserManager,
        action: str,
        state: AgentState,
        step_number: int
    ) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
        """
        Executes an action, captures observation and screenshot.
        Returns: (result_payload, observation_dict, screenshot_path)
        """
        if action not in REGISTERED_ACTIONS:
            raise ValueError(f"Action '{action}' is not in registered toolset. Arbitrary execution disallowed.")

        page = await browser_manager.get_page()
        result_payload: Dict[str, Any] = {}

        if action == "open_invoice_portal":
            result_payload = await InvoiceTools.open_portal(page)

        elif action == "search_company_invoices":
            company = state.get("target_company") or "Acme"
            result_payload = await InvoiceTools.search_company(page, company)

        elif action == "extract_latest_invoice":
            company = state.get("target_company") or "Acme"
            result_payload = await InvoiceTools.extract_latest_invoice(page, company)

        elif action == "open_billing_portal":
            fail_once = state.get("simulate_save_failure", False)
            result_payload = await BillingTools.open_portal(page, fail_once=fail_once)

        elif action == "fill_billing_form":
            extracted = state.get("extracted_data", {})
            result_payload = await BillingTools.fill_billing_form(
                page=page,
                company=extracted.get("company", state.get("target_company", "Acme")),
                invoice_id=extracted.get("invoice_id", "INV-1024"),
                amount=extracted.get("amount", "₹48,500"),
                due_date=extracted.get("due_date", "2026-10-15")
            )

        elif action == "submit_billing_record":
            simulate = state.get("simulate_save_failure", False)
            already_simulated = state.get("failure_simulated_done", False)
            fail_once = simulate and not already_simulated

            extracted = state.get("extracted_data", {})
            result_payload = await BillingTools.submit_billing_record(
                page=page,
                expected_data=extracted,
                fail_once=fail_once
            )

        elif action == "verify_billing_record":
            if "billing-portal" not in page.url:
                await BillingTools.open_portal(page)
            extracted = state.get("extracted_data", {})
            v_result, v_screenshot = await Verifier.verify_record(browser_manager, extracted)
            result_payload = {
                "action": "verify_billing_record",
                "status": "success" if v_result.get("verified") else "failed",
                "verification_result": v_result,
                "observation": (
                    f"Verification {'PASSED' if v_result.get('verified') else 'FAILED'}. "
                    f"Record ID: {v_result.get('record_id')}. Matching invoice: {v_result.get('invoice_id')}."
                )
            }
            obs, _ = await Observer.capture_observation(browser_manager, action, result_payload, step_number)
            return result_payload, obs, v_screenshot

        # Capture DOM observation and screenshot for other actions
        obs, screenshot_path = await Observer.capture_observation(
            browser_manager, action, result_payload, step_number
        )
        return result_payload, obs, screenshot_path
