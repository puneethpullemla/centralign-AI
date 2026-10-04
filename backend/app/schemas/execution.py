from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.schemas.task import ExecutionStepBrief, EvidenceBrief


class ExecutionHistoryResponse(BaseModel):
    task_id: str
    status: str
    current_step: int
    total_steps: int
    steps: List[ExecutionStepBrief]
    extracted_data: Optional[Dict[str, Any]] = None
    verification_result: Optional[Dict[str, Any]] = None


class EvidenceListResponse(BaseModel):
    task_id: str
    evidence_items: List[EvidenceBrief]
