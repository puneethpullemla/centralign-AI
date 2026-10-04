import os
import uuid
import logging
from typing import Optional, Tuple
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
from app.config import settings

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages the lifecycle of Playwright browser instances and pages."""

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        os.makedirs(settings.EVIDENCE_DIR, exist_ok=True)

    async def start(self) -> Page:
        """Launches browser and creates a clean context and page."""
        await self.close()

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=settings.PLAYWRIGHT_HEADLESS,
            slow_mo=settings.PLAYWRIGHT_SLOWMO_MS if not settings.PLAYWRIGHT_HEADLESS else 0
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            device_scale_factor=1
        )
        self._page = await self._context.new_page()
        return self._page

    async def get_page(self) -> Page:
        """Returns existing healthy page or starts a new session."""
        if self._page is not None and not self._page.is_closed():
            try:
                # Test connection health
                _ = self._page.url
                return self._page
            except Exception:
                logger.warning("Browser page disconnected. Re-launching browser session...")
                await self.close()

        return await self.start()

    async def capture_screenshot(self, name_prefix: str, description: str = "") -> Tuple[str, str]:
        """Captures a full-page screenshot and returns (relative_path, description)."""
        page = await self.get_page()
        os.makedirs(settings.EVIDENCE_DIR, exist_ok=True)
        filename = f"{name_prefix}_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(settings.EVIDENCE_DIR, filename)
        await page.screenshot(path=filepath, full_page=True)
        logger.info(f"Captured screenshot: {filepath} ({description})")
        return filepath, description

    async def close(self):
        """Closes browser context and Playwright session cleanly."""
        try:
            if self._page and not self._page.is_closed():
                await self._page.close()
        except Exception:
            pass
        try:
            if self._context:
                await self._context.close()
        except Exception:
            pass
        try:
            if self._browser:
                await self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
