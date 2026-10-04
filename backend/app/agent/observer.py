import logging
from typing import Dict, Any, Tuple
from playwright.async_api import Page
from app.tools.browser import BrowserManager

logger = logging.getLogger(__name__)


class Observer:
    """Captures DOM state, screenshots, and structured observations after tool execution."""

    @staticmethod
    async def capture_observation(
        browser_manager: BrowserManager,
        action_name: str,
        result_payload: Dict[str, Any],
        step_number: int
    ) -> Tuple[Dict[str, Any], str]:
        """
        Gathers URL, page title, screenshot, and human-readable observation summary.
        Returns: (observation_dict, screenshot_path)
        """
        page = await browser_manager.get_page()
        url = page.url
        title = await page.title()

        screenshot_prefix = f"step_{step_number}_{action_name}"
        screenshot_path, _ = await browser_manager.capture_screenshot(
            screenshot_prefix,
            description=f"Screenshot after executing {action_name}"
        )

        observation = {
            "action": action_name,
            "url": url,
            "title": title,
            "step_number": step_number,
            "status": result_payload.get("status", "success"),
            "details": result_payload.get("observation", f"Executed {action_name} successfully."),
            "screenshot": screenshot_path
        }

        # Include extracted data if present
        if "latest_invoice" in result_payload:
            observation["extracted_invoice"] = result_payload["latest_invoice"]
        if "record_id" in result_payload:
            observation["created_record_id"] = result_payload["record_id"]

        logger.info(f"Captured observation for step {step_number} ({action_name}): {observation['details']}")
        return observation, screenshot_path
