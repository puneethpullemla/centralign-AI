import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.dependencies import get_db
from app.schemas.task import TaskCreate, TaskDetailResponse
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])
logger = logging.getLogger(__name__)


@router.post("", response_model=TaskDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task_in: TaskCreate, db: Session = Depends(get_db)):
    """Accepts a natural language task description and initiates autonomous planning & execution."""
    logger.info(f"Received new task request: {task_in.user_task}")
    task = TaskService.create_task(db, task_in)
    return task


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(task_id: str, db: Session = Depends(get_db)):
    """Retrieves current state, plan, steps, and outcome of a specific task."""
    task = TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found."
        )
    return task
