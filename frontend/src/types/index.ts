export interface PlanStep {
  id: number;
  description: string;
  action: string;
  expected_outcome?: string;
}

export interface ExtractedData {
  invoice_id?: string;
  company?: string;
  date?: string;
  amount?: string;
  due_date?: string;
}

export interface ExecutionStep {
  id: string;
  step_number: number;
  action: string;
  status: 'PENDING' | 'RUNNING' | 'success' | 'failed' | 'retrying' | 'cancelled';
  observation?: any;
  error?: string | null;
  retry_count: number;
  started_at: string;
  completed_at?: string | null;
}

export interface Approval {
  id: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  payload?: ExtractedData | null;
  requested_at: string;
  resolved_at?: string | null;
}

export interface EvidenceItem {
  id: string;
  type: string;
  path: string;
  description?: string | null;
  created_at: string;
}

export interface Task {
  id: string;
  user_task: string;
  status: 'PENDING' | 'RUNNING' | 'AWAITING_APPROVAL' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  target_company?: string | null;
  plan?: PlanStep[] | null;
  extracted_data?: ExtractedData | null;
  completion_report?: string | null;
  created_at: string;
  completed_at?: string | null;
  steps: ExecutionStep[];
  approvals: Approval[];
  evidence_items: EvidenceItem[];
}
