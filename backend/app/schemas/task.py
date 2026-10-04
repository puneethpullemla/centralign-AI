from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class TaskCreate(BaseModel):
    user_task: str = Field(..., description="Natural language description of the task to perform", min_length=5)
    simulate_save_failure: bool = Field(False, description="Whether to simulate a temporary save failure in the billing system to demonstrate retry & recovery")


class TaskBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_task: str
    status: str
    target_company: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class ExecutionStepBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    step_number: int
    action: str
    status: str
    observation: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    started_at: datetime
    completed_at: Optional[datetime] = None


class ApprovalBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    payload: Optional[Dict[str, Any]] = None
    requested_at: datetime
    resolved_at: Optional[datetime] = None


class EvidenceBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    path: str
    description: Optional[str] = None
    created_at: datetime


class TaskDetailResponse(TaskBase):
    plan: Optional[List[Dict[str, Any]]] = None
    extracted_data: Optional[Dict[str, Any]] = None
    completion_report: Optional[str] = None
    steps: List[ExecutionStepBrief] = []
    approvals: List[ApprovalBrief] = []
    evidence_items: List[EvidenceBrief] = []
