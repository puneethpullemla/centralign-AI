import logging
from typing import Optional

from langgraph.graph import StateGraph, START, END

from app.agent.state import AgentState
from app.agent.planner import TaskPlanner
from app.agent.executor import ToolExecutor
from app.tools.browser import BrowserManager
from app.tools.billing_tools import BillingTools

logger = logging.getLogger(__name__)


class AgentWorkflow:
    """LangGraph workflow for the autonomous invoice processing agent."""

    def __init__(
        self,
        browser_manager: Optional[BrowserManager] = None,
        step_callback=None,
    ):
        self.browser_manager = browser_manager or BrowserManager()
        self.step_callback = step_callback
        self.graph = self._build_graph()

    # ============================================================
    # GRAPH
    # ============================================================

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node(
            "understand_and_plan",
            self.node_understand_and_plan,
        )

        workflow.add_node(
            "select_next_action",
            self.node_select_next_action,
        )

        workflow.add_node(
            "await_approval",
            self.node_await_approval,
        )

        workflow.add_node(
            "execute_tool",
            self.node_execute_tool,
        )

        workflow.add_node(
            "observe_and_evaluate",
            self.node_observe_and_evaluate,
        )

        workflow.add_node(
            "failure_recovery",
            self.node_failure_recovery,
        )

        workflow.add_node(
            "finalize_report",
            self.node_finalize_report,
        )

        # START
        workflow.add_edge(
            START,
            "understand_and_plan",
        )

        # Planning -> action selection
        workflow.add_edge(
            "understand_and_plan",
            "select_next_action",
        )

        # Action selection routing
        workflow.add_conditional_edges(
            "select_next_action",
            self.route_approval,
            {
                "await_approval": "await_approval",
                "execute": "execute_tool",
                "rejected": "finalize_report",
                "failed": "finalize_report",
                "done": "finalize_report",
            },
        )

        # Approval node ends the current run.
        # The task can later be resumed after approval.
        workflow.add_edge(
            "await_approval",
            END,
        )

        # Execute -> evaluate
        workflow.add_edge(
            "execute_tool",
            "observe_and_evaluate",
        )

        # Evaluation routing
        workflow.add_conditional_edges(
            "observe_and_evaluate",
            self.route_evaluation,
            {
                "next": "select_next_action",
                "retry": "failure_recovery",
                "finalize": "finalize_report",
            },
        )

        # Recovery routing
        workflow.add_conditional_edges(
            "failure_recovery",
            self.route_recovery,
            {
                "retry_action": "execute_tool",
                "next": "select_next_action",
                "failed": "finalize_report",
            },
        )

        # Final report
        workflow.add_edge(
            "finalize_report",
            END,
        )

        return workflow.compile()

    # ============================================================
    # PLANNER
    # ============================================================

    async def node_understand_and_plan(
        self,
        state: AgentState,
    ) -> AgentState:

        # --------------------------------------------------------
        # Resume an approved task.
        # Do not generate a new plan.
        # --------------------------------------------------------
        if (
            state.get("plan")
            and len(state["plan"]) > 0
            and state.get("current_step_index", 0) > 0
        ):
            logger.info(
                f"Task {state['task_id']}: "
                f"Resuming execution at step "
                f"{state['current_step_index']}."
            )

            return state

        logger.info(
            f"Task {state['task_id']}: "
            f"Understanding task and generating plan."
        )

        try:
            plan = await TaskPlanner.create_plan(
                state["user_prompt"]
            )
        except Exception as e:
            logger.exception(
                f"Planner failed for task {state['task_id']}: {e}"
            )

            state["status"] = "FAILED"
            state["plan"] = []
            state["current_step_index"] = 0

            error_message = (
                f"Unable to understand the task: {str(e)}"
            )

            state["errors"].append(error_message)
            state["completion_report"] = (
                f"Task rejected: {error_message}"
            )

            if self.step_callback:
                await self.step_callback(
                    state,
                    action="plan_created",
                    status="failed",
                    observation={
                        "message": state["completion_report"],
                        "valid_task": False,
                    },
                    error=error_message,
                )

            return state

        # --------------------------------------------------------
        # INVALID TASK
        #
        # Examples:
        # "hiiii"
        # "what is AI"
        # "gcghvhghdjghj"
        #
        # These should NEVER enter the browser workflow.
        # --------------------------------------------------------
        if not getattr(plan, "valid_task", True):

            rejection_reason = getattr(
                plan,
                "rejection_reason",
                None,
            ) or "Invalid or unsupported task."

            logger.warning(
                f"Task {state['task_id']} rejected by planner: "
                f"{rejection_reason}"
            )

            state["target_company"] = None
            state["plan"] = []
            state["current_step_index"] = 0
            state["status"] = "FAILED"

            state["errors"].append(
                rejection_reason
            )

            state["completion_report"] = (
                f"Task rejected: {rejection_reason}"
            )

            if self.step_callback:
                await self.step_callback(
                    state,
                    action="plan_created",
                    status="failed",
                    observation={
                        "message": state["completion_report"],
                        "valid_task": False,
                    },
                    error=rejection_reason,
                )

            return state

        # --------------------------------------------------------
        # VALID TASK
        # --------------------------------------------------------

        state["target_company"] = plan.target_company

        state["plan"] = [
            step.model_dump()
            for step in plan.steps
        ]

        state["status"] = "RUNNING"
        state["current_step_index"] = 0

        logger.info(
            f"Task {state['task_id']}: "
            f"Valid task detected. "
            f"Target company: {plan.target_company}"
        )

        if self.step_callback:
            await self.step_callback(
                state,
                action="plan_created",
                status="success",
                observation={
                    "plan": state["plan"],
                    "target_company": plan.target_company,
                    "valid_task": True,
                },
            )

        return state

    # ============================================================
    # ACTION SELECTION
    # ============================================================

    async def node_select_next_action(
        self,
        state: AgentState,
    ) -> AgentState:

        # Already failed/cancelled
        if state.get("status") in {
            "FAILED",
            "CANCELLED",
        }:
            return state

        # No remaining steps
        if (
            state["current_step_index"]
            >= len(state["plan"])
        ):
            return state

        step = state["plan"][
            state["current_step_index"]
        ]

        action = step["action"]

        logger.info(
            f"Task {state['task_id']}: "
            f"Next action = {action}"
        )

        # --------------------------------------------------------
        # Human approval before submitting billing record
        # --------------------------------------------------------

        if action == "submit_billing_record":

            if state.get("approval_status") == "APPROVED":

                state["requires_approval"] = False
                state["status"] = "RUNNING"

                logger.info(
                    f"Task {state['task_id']}: "
                    f"Human approval received."
                )

            elif state.get("approval_status") == "REJECTED":

                state["status"] = "CANCELLED"

                logger.info(
                    f"Task {state['task_id']}: "
                    f"Billing submission rejected."
                )

            else:

                state["requires_approval"] = True
                state["status"] = "AWAITING_APPROVAL"

                logger.info(
                    f"Task {state['task_id']}: "
                    f"Human approval required."
                )

        return state

    # ============================================================
    # APPROVAL
    # ============================================================

    async def node_await_approval(
        self,
        state: AgentState,
    ) -> AgentState:

        logger.info(
            f"Task {state['task_id']} "
            f"is awaiting human approval."
        )

        if self.step_callback:
            await self.step_callback(
                state,
                action="await_human_approval",
                status="pending",
                observation={
                    "message": (
                        "Human approval required to "
                        "submit billing record."
                    ),
                    "extracted_data": (
                        state.get("extracted_data")
                    ),
                },
            )

        await self.browser_manager.close()

        return state

    # ============================================================
    # EXECUTOR
    # ============================================================

    async def node_execute_tool(
        self,
        state: AgentState,
    ) -> AgentState:

        idx = state["current_step_index"]

        step = state["plan"][idx]

        action = step["action"]

        step_number = idx + 1

        logger.info(
            f"Task {state['task_id']}: "
            f"Executing step {step_number}: {action}"
        )

        try:

            result, obs, screenshot_path = (
                await ToolExecutor.execute_action(
                    self.browser_manager,
                    action,
                    state,
                    step_number,
                )
            )

            # ----------------------------------------------------
            # Observations
            # ----------------------------------------------------

            state["observations"].append(
                obs
            )

            state["screenshots"].append(
                {
                    "path": screenshot_path,
                    "description": obs.get(
                        "details",
                        "",
                    ),
                }
            )

            # ----------------------------------------------------
            # Extracted invoice data
            # ----------------------------------------------------

            if "latest_invoice" in result:

                state["extracted_data"] = (
                    result["latest_invoice"]
                )

            # ----------------------------------------------------
            # Billing record ID
            # ----------------------------------------------------

            if (
                "record_id" in result
                and result["record_id"]
            ):

                state["billing_record_id"] = (
                    result["record_id"]
                )

            # ----------------------------------------------------
            # Verification result
            # ----------------------------------------------------

            if "verification_result" in result:

                state["verification_result"] = (
                    result["verification_result"]
                )

            status = result.get(
                "status",
                "success",
            )

            # ----------------------------------------------------
            # Callback
            # ----------------------------------------------------

            if self.step_callback:

                await self.step_callback(
                    state,
                    action=action,
                    status=status,
                    observation=obs,
                    screenshot=screenshot_path,
                    error=result.get("error"),
                )

            # ----------------------------------------------------
            # Store execution result
            # ----------------------------------------------------

            state["last_action_result"] = result

            # ----------------------------------------------------
            # Simulated save failure
            # ----------------------------------------------------

            if (
                action == "submit_billing_record"
                and result.get("status") == "failed"
                and state.get("simulate_save_failure")
                and not state.get("failure_simulated_done")
            ):

                state["failure_simulated_done"] = True

                logger.info(
                    f"Task {state['task_id']}: "
                    f"Simulated failure marked as completed."
                )

        except Exception as e:

            logger.exception(
                f"Error executing action {action}: {e}"
            )

            error_message = str(e)

            state["errors"].append(
                error_message
            )

            state["last_action_result"] = {
                "status": "failed",
                "recoverable": True,
                "error": error_message,
            }

            if self.step_callback:

                await self.step_callback(
                    state,
                    action=action,
                    status="failed",
                    error=error_message,
                )

        return state

    # ============================================================
    # OBSERVE / EVALUATE
    # ============================================================

    async def node_observe_and_evaluate(
        self,
        state: AgentState,
    ) -> AgentState:

        last_result = (
            state.get("last_action_result")
            or {}
        )

        status = last_result.get("status")

        current_index = state[
            "current_step_index"
        ]

        current_action = None

        if (
            current_index < len(state["plan"])
        ):
            current_action = state[
                "plan"
            ][current_index]["action"]

        # --------------------------------------------------------
        # BUSINESS FAILURE:
        # Company has no invoices.
        #
        # Example:
        # "Find latest invoice from Infosys"
        #
        # This is NOT a retryable browser error.
        # --------------------------------------------------------

        if (
            current_action
            == "search_company_invoices"
        ):

            invoice_count = (
                last_result.get(
                    "invoice_count"
                )
            )

            if invoice_count is None:

                invoice_count = (
                    last_result.get("count")
                )

            if invoice_count is None:

                invoices = last_result.get(
                    "invoices"
                )

                if isinstance(
                    invoices,
                    list,
                ):
                    invoice_count = len(
                        invoices
                    )

            # Explicit zero-result case
            if invoice_count == 0:

                company = (
                    state.get(
                        "target_company"
                    )
                    or "requested company"
                )

                error_message = (
                    f"No invoices found for "
                    f"company '{company}'. "
                    f"The requested company is not "
                    f"present in the invoice portal."
                )

                logger.warning(
                    error_message
                )

                state["errors"].append(
                    error_message
                )

                state["status"] = "FAILED"

                state[
                    "last_action_result"
                ] = {
                    "status": "failed",
                    "recoverable": False,
                    "business_error": True,
                    "error": error_message,
                }

                state[
                    "recovery_decision"
                ] = "failed"

                return state

        # --------------------------------------------------------
        # Normal technical failure
        # --------------------------------------------------------

        if status == "failed":

            recoverable = last_result.get(
                "recoverable",
                True,
            )

            error_message = (
                last_result.get(
                    "error"
                )
                or "Action failed."
            )

            # Prevent duplicate errors
            if error_message not in state[
                "errors"
            ]:
                state["errors"].append(
                    error_message
                )

            if not recoverable:

                state["status"] = "FAILED"

                state[
                    "recovery_decision"
                ] = "failed"

                logger.error(
                    f"Non-recoverable failure: "
                    f"{error_message}"
                )

                return state

            logger.warning(
                f"Recoverable step failure: "
                f"{error_message}"
            )

            return state

        # --------------------------------------------------------
        # SUCCESS
        # --------------------------------------------------------

        state["retry_count"] = 0

        state["current_step_index"] += 1

        return state

    # ============================================================
    # FAILURE RECOVERY
    # ============================================================

    async def node_failure_recovery(
        self,
        state: AgentState,
    ) -> AgentState:

        idx = state["current_step_index"]

        # Safety check
        if idx >= len(state["plan"]):

            state[
                "recovery_decision"
            ] = "failed"

            return state

        action = state[
            "plan"
        ][idx]["action"]

        logger.info(
            f"Failure recovery for action: "
            f"{action}"
        )

        # --------------------------------------------------------
        # Never retry business failures
        # --------------------------------------------------------

        last_result = (
            state.get(
                "last_action_result"
            )
            or {}
        )

        if (
            last_result.get(
                "business_error"
            )
            or last_result.get(
                "recoverable"
            ) is False
        ):

            logger.warning(
                f"Non-recoverable/business "
                f"failure for {action}. "
                f"No retry."
            )

            state["status"] = "FAILED"

            state[
                "recovery_decision"
            ] = "failed"

            return state

        # --------------------------------------------------------
        # Duplicate billing protection
        # --------------------------------------------------------

        if action == "submit_billing_record":

            try:

                page = (
                    await self.browser_manager
                    .get_page()
                )

                invoice_id = (
                    state.get(
                        "extracted_data",
                        {},
                    ).get(
                        "invoice_id"
                    )
                )

                if invoice_id:

                    logger.info(
                        f"Checking whether "
                        f"{invoice_id} already exists."
                    )

                    if (
                        "billing-portal"
                        not in page.url
                    ):

                        await BillingTools.open_portal(
                            page
                        )

                    check_result = (
                        await BillingTools
                        .search_billing_record(
                            page,
                            invoice_id,
                        )
                    )

                    if check_result.get(
                        "found"
                    ):

                        record = (
                            check_result.get(
                                "record"
                            )
                            or {}
                        )

                        state[
                            "billing_record_id"
                        ] = record.get(
                            "record_id"
                        )

                        state[
                            "current_step_index"
                        ] += 1

                        state[
                            "recovery_decision"
                        ] = "next"

                        logger.info(
                            "Existing billing "
                            "record found. "
                            "Skipping duplicate "
                            "submission."
                        )

                        return state

            except Exception as e:

                logger.warning(
                    f"Duplicate-check failed: "
                    f"{e}"
                )

        # --------------------------------------------------------
        # Retry
        # --------------------------------------------------------

        if (
            state["retry_count"]
            < state["max_retries"]
        ):

            state["retry_count"] += 1

            logger.warning(
                f"Retrying {action}: "
                f"attempt "
                f"{state['retry_count']} "
                f"of "
                f"{state['max_retries']}"
            )

            if self.step_callback:

                await self.step_callback(
                    state,
                    action=f"retry_{action}",
                    status="retrying",
                    observation={
                        "retry_count": (
                            state["retry_count"]
                        ),
                        "message": (
                            f"Retrying {action} "
                            f"after recoverable "
                            f"failure."
                        ),
                    },
                )

            state[
                "recovery_decision"
            ] = "retry_action"

        else:

            logger.error(
                f"Action {action} exceeded "
                f"maximum retries "
                f"({state['max_retries']})."
            )

            state["status"] = "FAILED"

            state[
                "recovery_decision"
            ] = "failed"

        return state

    # ============================================================
    # FINAL REPORT
    # ============================================================

    async def node_finalize_report(
        self,
        state: AgentState,
    ) -> AgentState:

        logger.info(
            f"Task {state['task_id']}: "
            f"Finalizing report."
        )

        verification = (
            state.get(
                "verification_result"
            )
            or {}
        )

        is_verified = verification.get(
            "verified",
            False,
        )

        # --------------------------------------------------------
        # CANCELLED
        # --------------------------------------------------------

        if state.get(
            "status"
        ) == "CANCELLED":

            report = (
                "Task was rejected by the "
                "human operator and cancelled safely."
            )

        # --------------------------------------------------------
        # FAILED
        # --------------------------------------------------------

        elif state.get(
            "status"
        ) == "FAILED":

            errors = state.get(
                "errors",
                [],
            )

            if errors:

                report = (
                    "Task failed during execution. "
                    f"Errors: {'; '.join(errors)}"
                )

            else:

                report = (
                    "Task failed during execution."
                )

        # --------------------------------------------------------
        # VERIFIED SUCCESS
        # --------------------------------------------------------

        elif is_verified:

            state["status"] = "COMPLETED"

            extracted = (
                state.get(
                    "extracted_data",
                    {},
                )
            )

            report = (
                "Task completed successfully.\n\n"
                f"Company: "
                f"{extracted.get('company')}\n"
                f"Invoice ID: "
                f"{extracted.get('invoice_id')}\n"
                f"Amount: "
                f"{extracted.get('amount')}\n"
                f"Due Date: "
                f"{extracted.get('due_date')}\n"
                f"Billing Record ID: "
                f"{state.get('billing_record_id')}\n\n"
                "Verification: PASSED — "
                "Ledger record independently "
                "verified against the source invoice.\n"
                f"Evidence: "
                f"{len(state.get('screenshots', []))} "
                "screenshots captured."
            )

        # --------------------------------------------------------
        # Verification failed
        # --------------------------------------------------------

        else:

            state["status"] = "FAILED"

            report = (
                "Execution completed but "
                "independent verification failed. "
                "Ledger record does not match "
                "the source invoice."
            )

        state[
            "completion_report"
        ] = report

        if self.step_callback:

            await self.step_callback(
                state,
                action="complete_task",
                status=state[
                    "status"
                ].lower(),
                observation={
                    "report": report,
                    "verified": is_verified,
                },
            )

        await self.browser_manager.close()

        return state

    # ============================================================
    # ROUTING
    # ============================================================

    def route_approval(
        self,
        state: AgentState,
    ) -> str:

        status = state.get(
            "status"
        )

        # Invalid task / failed task
        if status == "FAILED":

            return "failed"

        # Human rejected
        if status == "CANCELLED":

            return "rejected"

        # Waiting for approval
        if status == "AWAITING_APPROVAL":

            return "await_approval"

        # No more steps
        if (
            state["current_step_index"]
            >= len(state["plan"])
        ):

            return "done"

        return "execute"

    def route_evaluation(
        self,
        state: AgentState,
    ) -> str:

        # --------------------------------------------------------
        # IMPORTANT:
        # If the task has already been marked FAILED,
        # NEVER retry it.
        #
        # This fixes:
        # "No invoices found for Infosys"
        # being retried repeatedly.
        # --------------------------------------------------------

        if state.get(
            "status"
        ) == "FAILED":

            return "finalize"

        last_result = (
            state.get(
                "last_action_result"
            )
            or {}
        )

        if last_result.get(
            "status"
        ) == "failed":

            # Business/non-recoverable failure
            if (
                last_result.get(
                    "business_error"
                )
                or last_result.get(
                    "recoverable"
                ) is False
            ):

                return "finalize"

            # Technical recoverable failure
            return "retry"

        # All steps completed
        if (
            state["current_step_index"]
            >= len(state["plan"])
        ):

            return "finalize"

        return "next"

    def route_recovery(
        self,
        state: AgentState,
    ) -> str:

        return state.get(
            "recovery_decision",
            "failed",
        )