import pytest
from unittest.mock import AsyncMock, patch
from app.agent.graph import AgentWorkflow
from app.agent.state import AgentState


@pytest.mark.asyncio
async def test_failure_recovery_bounded_retries():
    """Confirms agent respects MAX_RETRIES = 2 and fails safely when retries are exhausted."""
    workflow = AgentWorkflow()

    state: AgentState = {
        "task_id": "test-failure-task",
        "user_prompt": "Process Acme invoice",
        "target_company": "Acme",
        "plan": [
            {"id": 1, "description": "Submit billing", "action": "submit_billing_record"}
        ],
        "current_step_index": 0,
        "extracted_data": {"invoice_id": "INV-1024", "company": "Acme", "amount": "₹48,500", "due_date": "2026-10-15"},
        "observations": [],
        "action_history": [],
        "errors": [],
        "retry_count": 0,
        "max_retries": 2,
        "requires_approval": False,
        "approval_status": "APPROVED",
        "billing_record_id": None,
        "verification_result": None,
        "screenshots": [],
        "simulate_save_failure": True,
        "failure_simulated_done": False,
        "status": "RUNNING",
        "completion_report": None
    }

    # Mock billing tools search returning not found
    with patch("app.agent.graph.BillingTools.search_billing_record", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = {"found": False}

        # First failure recovery attempt
        state = await workflow.node_failure_recovery(state)
        assert state["retry_count"] == 1
        assert state["recovery_decision"] == "retry_action"

        # Second failure recovery attempt
        state = await workflow.node_failure_recovery(state)
        assert state["retry_count"] == 2
        assert state["recovery_decision"] == "retry_action"

        # Third attempt: exceeds max_retries
        state = await workflow.node_failure_recovery(state)
        assert state["recovery_decision"] == "failed"
        assert state["status"] == "FAILED"


@pytest.mark.asyncio
async def test_failure_recovery_duplicate_check_prevents_re_save():
    """Confirms that if ledger search reveals record was actually saved, agent does not re-submit."""
    workflow = AgentWorkflow()

    state: AgentState = {
        "task_id": "test-dup-task",
        "user_prompt": "Process Acme invoice",
        "target_company": "Acme",
        "plan": [
            {"id": 1, "description": "Submit billing", "action": "submit_billing_record"},
            {"id": 2, "description": "Verify record", "action": "verify_billing_record"}
        ],
        "current_step_index": 0,
        "extracted_data": {"invoice_id": "INV-1024", "company": "Acme"},
        "observations": [],
        "action_history": [],
        "errors": [],
        "retry_count": 0,
        "max_retries": 2,
        "requires_approval": False,
        "approval_status": "APPROVED",
        "billing_record_id": None,
        "verification_result": None,
        "screenshots": [],
        "simulate_save_failure": True,
        "failure_simulated_done": False,
        "status": "RUNNING",
        "completion_report": None
    }

    # Simulate that duplicate check in ledger finds the record already created
    with patch("app.agent.graph.BillingTools.search_billing_record", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = {
            "found": True,
            "record": {"record_id": "BILL-7842", "invoice_id": "INV-1024", "company": "Acme"}
        }

        state = await workflow.node_failure_recovery(state)

        # Should recover without re-executing submit
        assert state["recovery_decision"] == "next"
        assert state["billing_record_id"] == "BILL-7842"
        assert state["current_step_index"] == 1
