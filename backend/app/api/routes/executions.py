import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.dependencies import get_db
from app.models.task import Task
from app.models.evidence import Evidence
from app.schemas.execution import ExecutionHistoryResponse, EvidenceListResponse
from app.schemas.task import ExecutionStepBrief, EvidenceBrief

router = APIRouter(prefix="/tasks", tags=["Executions"])
logger = logging.getLogger(__name__)


@router.get("/{task_id}/execution", response_model=ExecutionHistoryResponse)
def get_execution_history(task_id: str, db: Session = Depends(get_db)):
    """Returns the ordered timeline of execution steps, observations, and status."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    steps_data = [ExecutionStepBrief.model_validate(s) for s in task.steps]
    total_steps = len(task.plan) if task.plan else len(steps_data)
    current_step = len(steps_data)

    return ExecutionHistoryResponse(
        task_id=task.id,
        status=task.status,
        current_step=current_step,
        total_steps=total_steps,
        steps=steps_data,
        extracted_data=task.extracted_data,
        verification_result=task.steps[-1].observation.get("verification_result") if task.steps and task.steps[-1].observation and "verification_result" in task.steps[-1].observation else None
    )


@router.get("/{task_id}/evidence", response_model=EvidenceListResponse)
def get_evidence(task_id: str, db: Session = Depends(get_db)):
    """Returns all evidence items and screenshots generated for a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    evidence_records = db.query(Evidence).filter(Evidence.task_id == task_id).all()
    return EvidenceListResponse(
        task_id=task.id,
        evidence_items=[EvidenceBrief.model_validate(e) for e in evidence_records]
    )
