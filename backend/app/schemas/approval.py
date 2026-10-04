from typing import Optional
from pydantic import BaseModel


class ApprovalDecision(BaseModel):
    notes: Optional[str] = None


class ApprovalResponse(BaseModel):
    task_id: str
    approval_id: str
    status: str
    message: str
