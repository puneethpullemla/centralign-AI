import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.dependencies import get_db
from app.schemas.approval import ApprovalDecision, ApprovalResponse
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Approvals"])
logger = logging.getLogger(__name__)


@router.post("/{task_id}/approve", response_model=ApprovalResponse)
async def approve_task(task_id: str, decision: ApprovalDecision = ApprovalDecision(), db: Session = Depends(get_db)):
    """Approves a pending task action to resume execution."""
    logger.info(f"Operator approved task {task_id}")
    try:
        approval = TaskService.approve_task(db, task_id, decision.notes)
        return ApprovalResponse(
            task_id=task_id,
            approval_id=approval.id,
            status=approval.status,
            message="Task action approved. Resuming agent execution pipeline."
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{task_id}/reject", response_model=ApprovalResponse)
async def reject_task(task_id: str, decision: ApprovalDecision = ApprovalDecision(), db: Session = Depends(get_db)):
    """Rejects a pending task action and safely cancels the task."""
    logger.info(f"Operator rejected task {task_id}")
    try:
        approval = TaskService.reject_task(db, task_id, decision.notes)
        return ApprovalResponse(
            task_id=task_id,
            approval_id=approval.id,
            status=approval.status,
            message="Task action rejected. Agent terminated safely."
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
