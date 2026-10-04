import asyncio
import logging
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.task import Task
from app.models.execution import ExecutionStep
from app.models.approval import Approval
from app.models.evidence import Evidence
from app.schemas.task import TaskCreate
from app.agent.graph import AgentWorkflow
from app.agent.state import AgentState
from app.tools.browser import BrowserManager
from app.config import settings

logger = logging.getLogger(__name__)

# Active background runners registry to preserve browser instance during human approval
_active_browser_managers: Dict[str, BrowserManager] = {}
_active_states: Dict[str, AgentState] = {}


def now_utc():
    return datetime.now(timezone.utc)


def schedule_background_coroutine(coro):
    """Schedules an async coroutine either in the current loop or in a daemon thread."""
    try:
        loop = asyncio.get_running_loop()
        return loop.create_task(coro)
    except RuntimeError:
        thread = threading.Thread(target=lambda: asyncio.run(coro))
        thread.daemon = True
        thread.start()
        return thread


class TaskService:
    @staticmethod
    def create_task(db: Session, task_in: TaskCreate) -> Task:
        new_task = Task(
            user_task=task_in.user_task,
            status="PENDING"
        )
        db.add(new_task)
        db.commit()
        db.refresh(new_task)

        # Trigger background execution asynchronously
        schedule_background_coroutine(
            TaskService.execute_task_pipeline(
                task_id=new_task.id,
                simulate_save_failure=task_in.simulate_save_failure
            )
        )
        return new_task

    @staticmethod
    def get_task(db: Session, task_id: str) -> Optional[Task]:
        return db.query(Task).filter(Task.id == task_id).first()

    @staticmethod
    async def execute_task_pipeline(
        task_id: str,
        approval_decision: Optional[str] = None,
        simulate_save_failure: bool = False
    ):
        """Orchestrates LangGraph agent execution and synchronizes DB state."""
        db: Session = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                logger.error(f"Task {task_id} not found in database.")
                return

            # Always create fresh BrowserManager instance for the execution lifecycle
            browser_manager = BrowserManager()
            _active_browser_managers[task_id] = browser_manager

            # Callback for recording steps and evidence dynamically
            async def step_callback(
                state: AgentState,
                action: str,
                status: str,
                observation: Optional[Dict[str, Any]] = None,
                screenshot: Optional[str] = None,
                error: Optional[str] = None
            ):
                s_db: Session = SessionLocal()
                try:
                    s_task = s_db.query(Task).filter(Task.id == task_id).first()
                    if s_task:
                        s_task.status = state.get("status", s_task.status)
                        s_task.plan = state.get("plan")
                        s_task.target_company = state.get("target_company")
                        s_task.extracted_data = state.get("extracted_data")

                    # Record execution step
                    step_num = state.get("current_step_index", 0) + 1
                    step_record = ExecutionStep(
                        task_id=task_id,
                        step_number=step_num,
                        action=action,
                        status=status,
                        observation=observation,
                        error=error,
                        retry_count=state.get("retry_count", 0),
                        completed_at=now_utc() if status in ("success", "failed", "cancelled") else None
                    )
                    s_db.add(step_record)
                    s_db.commit()
                    s_db.refresh(step_record)

                    # Record screenshot evidence if present
                    if screenshot:
                        ev = Evidence(
                            task_id=task_id,
                            step_id=step_record.id,
                            type="SCREENSHOT",
                            path=screenshot,
                            description=f"Action '{action}' result screenshot"
                        )
                        s_db.add(ev)
                        s_db.commit()

                    # Record approval request if needed
                    if state.get("status") == "AWAITING_APPROVAL":
                        existing_appr = s_db.query(Approval).filter(
                            Approval.task_id == task_id,
                            Approval.status == "PENDING"
                        ).first()
                        if not existing_appr:
                            appr = Approval(
                                task_id=task_id,
                                status="PENDING",
                                payload=state.get("extracted_data")
                            )
                            s_db.add(appr)
                            s_db.commit()

                except Exception as ex:
                    logger.error(f"Error in step callback: {ex}")
                finally:
                    s_db.close()

            # Retrieve or build state
            state = _active_states.get(task_id)
            if not state:
                state = AgentState(
                    task_id=task_id,
                    user_prompt=task.user_task,
                    target_company=task.target_company,
                    plan=task.plan or [],
                    current_step_index=0,
                    extracted_data=task.extracted_data or {},
                    observations=[],
                    action_history=[],
                    errors=[],
                    retry_count=0,
                    max_retries=settings.MAX_RETRIES,
                    requires_approval=False,
                    approval_status=approval_decision,
                    billing_record_id=None,
                    verification_result=None,
                    screenshots=[],
                    simulate_save_failure=simulate_save_failure,
                    failure_simulated_done=False,
                    status="RUNNING",
                    completion_report=None
                )
            else:
                if approval_decision:
                    state["approval_status"] = approval_decision
                    if approval_decision == "APPROVED":
                        state["status"] = "RUNNING"
                        state["requires_approval"] = False
                    elif approval_decision == "REJECTED":
                        state["status"] = "CANCELLED"

            _active_states[task_id] = state

            # Execute LangGraph workflow
            workflow = AgentWorkflow(browser_manager=browser_manager, step_callback=step_callback)
            final_state = await workflow.graph.ainvoke(state)
            _active_states[task_id] = final_state

            # Sync final state to DB
            task.status = final_state["status"]
            task.plan = final_state.get("plan")
            task.target_company = final_state.get("target_company")
            task.extracted_data = final_state.get("extracted_data")
            task.completion_report = final_state.get("completion_report")

            if final_state["status"] in ("COMPLETED", "FAILED", "CANCELLED"):
                task.completed_at = now_utc()
                # Clean up active memory
                if task_id in _active_browser_managers:
                    del _active_browser_managers[task_id]
                if task_id in _active_states:
                    del _active_states[task_id]

            db.commit()

        except Exception as e:
            logger.error(f"Unhandled error in task pipeline for {task_id}: {e}", exc_info=True)
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = "FAILED"
                task.completion_report = f"Pipeline execution failed: {str(e)}"
                task.completed_at = now_utc()
                db.commit()
        finally:
            db.close()

    @staticmethod
    def approve_task(db: Session, task_id: str, notes: Optional[str] = None) -> Approval:
        approval = db.query(Approval).filter(
            Approval.task_id == task_id,
            Approval.status == "PENDING"
        ).first()

        if not approval:
            raise ValueError("No pending approval found for this task.")

        approval.status = "APPROVED"
        approval.resolved_at = now_utc()
        db.commit()
        db.refresh(approval)

        # Resume agent pipeline
        schedule_background_coroutine(
            TaskService.execute_task_pipeline(task_id=task_id, approval_decision="APPROVED")
        )
        return approval

    @staticmethod
    def reject_task(db: Session, task_id: str, notes: Optional[str] = None) -> Approval:
        approval = db.query(Approval).filter(
            Approval.task_id == task_id,
            Approval.status == "PENDING"
        ).first()

        if not approval:
            raise ValueError("No pending approval found for this task.")

        approval.status = "REJECTED"
        approval.resolved_at = now_utc()

        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = "CANCELLED"
            task.completed_at = now_utc()
            task.completion_report = "Task rejected by operator. Safe cancellation confirmed."

        db.commit()
        db.refresh(approval)

        # Resume agent pipeline with rejection
        schedule_background_coroutine(
            TaskService.execute_task_pipeline(task_id=task_id, approval_decision="REJECTED")
        )
        return approval
