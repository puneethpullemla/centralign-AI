import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application
    APP_NAME: str = "Autonomous AI Task Worker"
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:5173"
    EVIDENCE_DIR: str = "./evidence"
    MAX_RETRIES: int = 2

    # LLM Settings
    LLM_PROVIDER: str = "gemini"  # "gemini" or "openai"
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gemini-flash-latest"

    # Database
    DATABASE_URL: str = "sqlite:///./app.db"

    # Browser / Playwright
    PLAYWRIGHT_HEADLESS: bool = True
    PLAYWRIGHT_SLOWMO_MS: int = 250

    # Sandboxes
    INVOICE_PORTAL_URL: str = "http://localhost:8000/sandbox/invoice-portal"
    BILLING_PORTAL_URL: str = "http://localhost:8000/sandbox/billing-portal"

    @property
    def effective_llm_provider(self) -> str:
        """Determines effective LLM provider based on set keys if not explicitly defined."""
        if self.LLM_PROVIDER:
            prov = self.LLM_PROVIDER.lower()
            if prov in ("gemini", "google") and (self.GEMINI_API_KEY or self.GOOGLE_API_KEY):
                return "gemini"
            if prov == "openai" and self.OPENAI_API_KEY:
                return "openai"
        if self.OPENAI_API_KEY:
            return "openai"
        if self.GEMINI_API_KEY or self.GOOGLE_API_KEY:
            return "gemini"
        return "openai"


settings = Settings()
