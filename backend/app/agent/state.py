from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict):
    task_id: str
    user_prompt: str
    target_company: Optional[str]

    valid_task: bool
    rejection_reason: Optional[str]

    plan: List[Dict[str, Any]]
    current_step_index: int
    extracted_data: Dict[str, Any]
    observations: List[Dict[str, Any]]
    action_history: List[Dict[str, Any]]
    errors: List[str]
    retry_count: int
    max_retries: int
    requires_approval: bool
    approval_status: Optional[str]
    billing_record_id: Optional[str]
    verification_result: Optional[Dict[str, Any]]
    screenshots: List[Dict[str, str]]
    simulate_save_failure: bool
    failure_simulated_done: bool
    last_action_result: Optional[Dict[str, Any]]
    recovery_decision: Optional[str]
    status: str
    completion_report: Optional[str]