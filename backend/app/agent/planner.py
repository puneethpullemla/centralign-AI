import os
import json
import re
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.config import settings
from app.agent.prompts import PLANNER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class PlanStep(BaseModel):
    id: int
    description: str
    action: str
    expected_outcome: Optional[str] = None


class StructuredPlan(BaseModel):
    goal: str
    target_company: Optional[str] = None
    valid_task: bool = Field(
        default=True,
        description="Whether the user request is a valid invoice processing task"
    )
    rejection_reason: Optional[str] = None
    steps: List[PlanStep] = [] 

def get_llm():
    """Initializes LLM instance according to configuration."""
    provider = settings.effective_llm_provider

    if provider == "openai" and (settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.LLM_MODEL or "gpt-4o",
            temperature=0,
            api_key=settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")
        )

    if provider == "gemini" and (settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY or os.environ.get("GEMINI_API_KEY")):
        from langchain_google_genai import ChatGoogleGenerativeAI
        key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY or os.environ.get("GEMINI_API_KEY")
        model_name = settings.LLM_MODEL
        if not model_name or model_name.startswith("gpt"):
            model_name = "gemini-flash-latest"
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0,
            google_api_key=key
        )

    return None


class TaskPlanner:
    """Plans autonomous task execution by discovering goals and decomposing actions."""

    @classmethod
    async def create_plan(cls, user_task: str) -> StructuredPlan:
        llm = get_llm()

        if llm:
            try:
                logger.info(f"Invoking LLM ({settings.effective_llm_provider}) for task planning")
                # Using structured output
                structured_llm = llm.with_structured_output(StructuredPlan)
                prompt_text = f"{PLANNER_SYSTEM_PROMPT}\n\nUser Task: {user_task}"
                result = await structured_llm.ainvoke(prompt_text)
                if isinstance(result, StructuredPlan):
                    logger.info(f"LLM generated plan successfully for target company: {result.target_company}")
                    return result
            except Exception as e:
                logger.warning(f"LLM planning failed with error: {e}. Falling back to deterministic planner.")

        # Fallback deterministic planner (handles generalization dynamically)
        return cls._create_deterministic_plan(user_task)

    @classmethod
    def _create_deterministic_plan(cls, user_task: str) -> StructuredPlan:
        task = user_task.strip()

        # Basic validation
        if not task:
            return StructuredPlan(
                goal="",
                target_company=None,
                valid_task=False,
                rejection_reason="Empty task.",
                steps=[]
            )

        # Task must be related to invoice processing
        invoice_keywords = [
            "invoice",
            "billing",
            "bill",
            "vendor invoice",
            "billing record"
        ]

        if not any(keyword in task.lower() for keyword in invoice_keywords):
            return StructuredPlan(
                goal=task,
                target_company=None,
                valid_task=False,
                rejection_reason=(
                    "Invalid task. Please provide a task related to "
                    "finding an invoice and processing it in the billing system."
                ),
                steps=[]
            )

        # Extract company from:
        # "invoice from Acme"
        # "latest invoice from Infosys"
        match = re.search(
            r"(?:invoice|invoices)\s+from\s+([A-Za-z0-9_.-]+)",
            task,
            re.IGNORECASE
        )

        # Also support:
        # "from Acme invoice"
        if not match:
            match = re.search(
                r"from\s+([A-Za-z0-9_.-]+)",
                task,
                re.IGNORECASE
            )

        if not match:
            return StructuredPlan(
                goal=task,
                target_company=None,
                valid_task=False,
                rejection_reason=(
                    "Could not identify the company. "
                    "Please specify the company name."
                ),
                steps=[]
            )

        company = match.group(1).strip()

        return StructuredPlan(
            goal=f"Process latest invoice for {company} and record in billing system",
            target_company=company,
            valid_task=True,
            rejection_reason=None,
            steps=[
                PlanStep(
                    id=1,
                    description="Open invoice portal",
                    action="open_invoice_portal",
                    expected_outcome="Invoice Portal visible"
                ),
                PlanStep(
                    id=2,
                    description=f"Search {company} invoices",
                    action="search_company_invoices",
                    expected_outcome=f"Invoices for {company} listed"
                ),
                PlanStep(
                    id=3,
                    description=f"Extract latest {company} invoice details",
                    action="extract_latest_invoice",
                    expected_outcome="Amount, date, and due date extracted"
                ),
                PlanStep(
                    id=4,
                    description="Open internal billing portal",
                    action="open_billing_portal",
                    expected_outcome="Billing system visible"
                ),
                PlanStep(
                    id=5,
                    description="Fill billing form with extracted data",
                    action="fill_billing_form",
                    expected_outcome="Form fields populated"
                ),
                PlanStep(
                    id=6,
                    description="Submit billing record to ledger",
                    action="submit_billing_record",
                    expected_outcome="Record saved or error caught"
                ),
                PlanStep(
                    id=7,
                    description="Verify saved record in billing ledger",
                    action="verify_billing_record",
                    expected_outcome="Ledger verification confirmed"
                )
            ]
        )