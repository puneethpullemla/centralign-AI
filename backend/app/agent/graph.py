import logging
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from app.agent.state import AgentState
from app.agent.planner import TaskPlanner
from app.agent.executor import ToolExecutor
from app.tools.browser import BrowserManager
from app.tools.billing_tools import BillingTools

logger = logging.getLogger(__name__)


class AgentWorkflow:
    """LangGraph workflow encapsulating the autonomous agent lifecycle."""

    def __init__(self, browser_manager: Optional[BrowserManager] = None, step_callback=None):
        self.browser_manager = browser_manager or BrowserManager()
        self.step_callback = step_callback
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("understand_and_plan", self.node_understand_and_plan)
        workflow.add_node("select_next_action", self.node_select_next_action)
        workflow.add_node("await_approval", self.node_await_approval)
        workflow.add_node("execute_tool", self.node_execute_tool)
        workflow.add_node("observe_and_evaluate", self.node_observe_and_evaluate)
        workflow.add_node("failure_recovery", self.node_failure_recovery)
        workflow.add_node("finalize_report", self.node_finalize_report)

        # Edges
        workflow.add_edge(START, "understand_and_plan")
        workflow.add_edge("understand_and_plan", "select_next_action")

        workflow.add_conditional_edges(
            "select_next_action",
            self.route_approval,
            {
                "await_approval": "await_approval",
                "execute": "execute_tool",
                "rejected": "finalize_report",
                "done": "finalize_report"
            }
        )

        workflow.add_edge("await_approval", END)
        workflow.add_edge("execute_tool", "observe_and_evaluate")

        workflow.add_conditional_edges(
            "observe_and_evaluate",
            self.route_evaluation,
            {
                "next": "select_next_action",
                "retry": "failure_recovery",
                "finalize": "finalize_report"
            }
        )

        workflow.add_conditional_edges(
            "failure_recovery",
            self.route_recovery,
            {
                "retry_action": "execute_tool",
                "next": "select_next_action",
                "failed": "finalize_report"
            }
        )

        workflow.add_edge("finalize_report", END)

        return workflow.compile()

    # --- Nodes ---

    async def node_understand_and_plan(self, state: AgentState) -> AgentState:
        # If resuming an approved task with existing plan, preserve current plan and position
        if state.get("plan") and len(state["plan"]) > 0 and state.get("current_step_index", 0) > 0:
            logger.info(f"Task {state['task_id']}: Resuming execution at step index {state['current_step_index']}.")
            return state

        logger.info(f"Task {state['task_id']}: Understanding task & generating plan")
        plan = await TaskPlanner.create_plan(state["user_prompt"])
        state["target_company"] = plan.target_company
        state["plan"] = [step.model_dump() for step in plan.steps]
        state["status"] = "RUNNING"
        state["current_step_index"] = 0

        if self.step_callback:
            await self.step_callback(state, action="plan_created", status="success", observation={"plan": state["plan"]})
        return state

    async def node_select_next_action(self, state: AgentState) -> AgentState:
        idx = state["current_step_index"]
        if idx >= len(state["plan"]):
            return state

        current_step = state["plan"][idx]
        action = current_step["action"]

        # Check if human approval is required for submitting billing record
        if action == "submit_billing_record":
            if state.get("approval_status") == "APPROVED":
                state["requires_approval"] = False
                state["status"] = "RUNNING"
                logger.info(f"Task {state['task_id']}: Operator approval received. Proceeding with submit_billing_record.")
            elif state.get("approval_status") == "REJECTED":
                state["status"] = "CANCELLED"
            else:
                state["requires_approval"] = True
                state["status"] = "AWAITING_APPROVAL"
                logger.info(f"Task {state['task_id']} pausing: Human approval required before submitting billing record.")

        return state

    async def node_await_approval(self, state: AgentState) -> AgentState:
        logger.info(f"Task {state['task_id']} is awaiting human approval.")
        if self.step_callback:
            await self.step_callback(
                state,
                action="await_human_approval",
                status="pending",
                observation={
                    "message": "Human approval required to submit billing record.",
                    "extracted_data": state.get("extracted_data")
                }
            )
        await self.browser_manager.close()
        return state

    async def node_execute_tool(self, state: AgentState) -> AgentState:
        idx = state["current_step_index"]
        step = state["plan"][idx]
        action = step["action"]
        step_number = idx + 1

        logger.info(f"Task {state['task_id']}: Executing step {step_number} ({action})")

        try:
            result, obs, screenshot_path = await ToolExecutor.execute_action(
                self.browser_manager, action, state, step_number
            )
            state["observations"].append(obs)
            state["screenshots"].append({"path": screenshot_path, "description": obs.get("details", "")})

            # Update extracted data or record IDs
            if "latest_invoice" in result:
                state["extracted_data"] = result["latest_invoice"]
            if "record_id" in result and result["record_id"]:
                state["billing_record_id"] = result["record_id"]
            if "verification_result" in result:
                state["verification_result"] = result["verification_result"]

            status = result.get("status", "success")

            if self.step_callback:
                await self.step_callback(
                    state,
                    action=action,
                    status=status,
                    observation=obs,
                    screenshot=screenshot_path,
                    error=result.get("error")
                )

            # Store last execution outcome on state for evaluation
            state["last_action_result"] = result

            # If this was a simulated failure on submit, mark it done so retries skip fail_once
            if (
                action == "submit_billing_record"
                and result.get("status") == "failed"
                and state.get("simulate_save_failure")
                and not state.get("failure_simulated_done")
            ):
                state["failure_simulated_done"] = True
                logger.info(f"Task {state['task_id']}: Marked failure_simulated_done=True — retries will not re-simulate error.")
        except Exception as e:
            logger.error(f"Error executing action {action}: {e}")
            state["errors"].append(str(e))
            state["last_action_result"] = {"status": "failed", "error": str(e)}
            if self.step_callback:
                await self.step_callback(state, action=action, status="failed", error=str(e))

        return state

    async def node_observe_and_evaluate(self, state: AgentState) -> AgentState:
        last_result = state.get("last_action_result") or {}
        status = last_result.get("status")

        if status == "failed":
            logger.warning(f"Step failed. Routing to failure recovery: {last_result.get('error')}")
            return state

        # If success, advance step
        state["retry_count"] = 0
        state["current_step_index"] += 1
        return state

    async def node_failure_recovery(self, state: AgentState) -> AgentState:
        idx = state["current_step_index"]
        action = state["plan"][idx]["action"]
        logger.info(f"Initiating failure recovery for action: {action}")

        # Check duplicate scenario before retrying submit_billing_record
        if action == "submit_billing_record":
            page = await self.browser_manager.get_page()
            invoice_id = state.get("extracted_data", {}).get("invoice_id")
            if invoice_id:
                logger.info(f"Checking whether record {invoice_id} was already created in ledger before retrying...")
                if "billing-portal" not in page.url:
                    await BillingTools.open_portal(page)
                check_result = await BillingTools.search_billing_record(page, invoice_id)
                if check_result.get("found"):
                    logger.info("Ledger search revealed record already exists! Recovered safely without duplicate creation.")
                    state["billing_record_id"] = check_result["record"]["record_id"]
                    state["current_step_index"] += 1
                    state["recovery_decision"] = "next"
                    return state

        # If not created and retries remain
        if state["retry_count"] < state["max_retries"]:
            state["retry_count"] += 1
            logger.warning(f"Retrying action {action} (attempt {state['retry_count']} of {state['max_retries']})")
            if self.step_callback:
                await self.step_callback(
                    state,
                    action=f"retry_{action}",
                    status="retrying",
                    observation={"retry_count": state["retry_count"], "message": f"Retrying {action} after recoverable failure."}
                )
            state["recovery_decision"] = "retry_action"
        else:
            logger.error(f"Action {action} exceeded maximum retries ({state['max_retries']}). Terminating task.")
            state["status"] = "FAILED"
            state["recovery_decision"] = "failed"

        return state

    async def node_finalize_report(self, state: AgentState) -> AgentState:
        logger.info(f"Task {state['task_id']}: Finalizing report")

        # Check verification status
        v_result = state.get("verification_result", {})
        is_verified = v_result.get("verified", False) if v_result else False

        if state.get("status") == "CANCELLED":
            report = "Task was rejected by human operator and cancelled safely."
        elif state.get("status") == "FAILED":
            report = f"Task failed during execution. Errors: {'; '.join(state.get('errors', []))}"
        elif is_verified:
            state["status"] = "COMPLETED"
            ext = state.get("extracted_data", {})
            report = (
                f"Task completed successfully.\n\n"
                f"Company: {ext.get('company')}\n"
                f"Invoice ID: {ext.get('invoice_id')}\n"
                f"Amount: {ext.get('amount')}\n"
                f"Due Date: {ext.get('due_date')}\n"
                f"Billing Record ID: {state.get('billing_record_id')}\n\n"
                f"Verification: PASSED — Ledger record independently verified matching source invoice.\n"
                f"Evidence: {len(state.get('screenshots', []))} screenshots captured."
            )
        else:
            state["status"] = "FAILED"
            report = "Execution completed but independent verification failed. Ledger record does not match source invoice."

        state["completion_report"] = report

        if self.step_callback:
            await self.step_callback(
                state,
                action="complete_task",
                status=state["status"].lower(),
                observation={"report": report, "verified": is_verified}
            )

        # Close browser session
        await self.browser_manager.close()
        return state

    # --- Routing functions ---

    def route_approval(self, state: AgentState) -> str:
        if state.get("status") == "CANCELLED":
            return "rejected"
        if state.get("status") == "AWAITING_APPROVAL":
            return "await_approval"
        if state["current_step_index"] >= len(state["plan"]):
            return "done"
        return "execute"

    def route_evaluation(self, state: AgentState) -> str:
        last_result = state.get("last_action_result") or {}
        if last_result.get("status") == "failed":
            return "retry"
        if state["current_step_index"] >= len(state["plan"]):
            return "finalize"
        return "next"

    def route_recovery(self, state: AgentState) -> str:
        return state.get("recovery_decision", "failed")
