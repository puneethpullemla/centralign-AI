import pytest
from app.agent.planner import TaskPlanner
from app.agent.executor import REGISTERED_ACTIONS, ToolExecutor
from app.agent.state import AgentState


@pytest.mark.asyncio
async def test_planner_generalization_acme():
    prompt = "Find the latest invoice from Acme, extract amount and due date, enter into billing system"
    plan = await TaskPlanner.create_plan(prompt)

    assert plan.target_company == "Acme"
    assert len(plan.steps) >= 5
    actions = [s.action for s in plan.steps]
    assert "open_invoice_portal" in actions
    assert "extract_latest_invoice" in actions
    assert "submit_billing_record" in actions
    assert "verify_billing_record" in actions


@pytest.mark.asyncio
async def test_planner_generalization_globex():
    prompt = "Please retrieve the latest Globex invoice and input into the internal billing records"
    plan = await TaskPlanner.create_plan(prompt)

    assert plan.target_company.lower() == "globex"
    actions = [s.action for s in plan.steps]
    assert "verify_billing_record" in actions


@pytest.mark.asyncio
async def test_safety_unregistered_action():
    state: AgentState = {
        "task_id": "test",
        "user_prompt": "test",
        "target_company": "Acme",
        "plan": [],
        "current_step_index": 0,
        "extracted_data": {},
        "observations": [],
        "action_history": [],
        "errors": [],
        "retry_count": 0,
        "max_retries": 2,
        "requires_approval": False,
        "approval_status": None,
        "billing_record_id": None,
        "verification_result": None,
        "screenshots": [],
        "simulate_save_failure": False,
        "failure_simulated_done": False,
        "status": "RUNNING",
        "completion_report": None
    }

    class DummyBrowserManager:
        pass

    with pytest.raises(ValueError, match="not in registered toolset"):
        await ToolExecutor.execute_action(DummyBrowserManager(), "malicious_eval_script", state, 1)
