export type Role = 'technician' | 'supervisor';

export interface User {
  id: string;
  username: string;
  role: Role;
  full_name: string;
}

export interface Asset {
  asset_id: string;
  name: string;
  category: string;
  model: string;
  location: string;
  critical_rating: string;
  last_inspection_date: string;
  days_since_inspection: number;
  readiness_score: number;
  status_label: string;
  badge_color: 'green' | 'amber' | 'red';
  open_work_orders_count: number;
  is_superseded_manual: boolean;
  superseded_warning?: string | null;
  penalties: string[];
  flags: string[];
}

export interface CauseCard {
  cause_id: string;
  name: string;
  label: 'Documented' | 'Observed' | 'Inferred' | 'Verified';
  evidence_strength: 'high' | 'moderate' | 'low';
  evidence_reasons?: string[];
  source_doc_id: string;
  section: string;
  explanation?: string;
  recommended_procedure_id?: string;
}

export interface SafetyAlert {
  hazard_type: string;
  matched_text: string;
  emergency_action: string;
  procedure_id: string;
}

export interface DiagnosisMetadata {
  asset: any;
  symptom: any;
  safety_alert?: SafetyAlert | null;
  ranked_causes: CauseCard[];
  retrieval_ms: number;
}

export interface Finding {
  id: string;
  finding_type: string;
  component_id?: string;
  parameter?: string;
  value?: string;
  notes: string;
  created_at: string;
}

export interface WorkOrder {
  id: string;
  session_id?: string;
  asset_id: string;
  title: string;
  status: 'draft' | 'assigned' | 'in_progress' | 'pending_approval' | 'approved' | 'rejected';
  priority: 'critical' | 'high' | 'medium' | 'low';
  assignee_id?: string;
  required_parts: string[];
  findings_summary?: string;
  resolution_confirmed_cause?: string;
  resolution_action_taken?: string;
  resolution_parts_used?: string;
  resolution_result?: string;
  submitted_by?: string;
  submitted_at?: string;
  approved_by?: string;
  approved_at?: string;
  rejection_reason?: string;
  created_at: string;
}

export interface RecurringCluster {
  asset_id: string;
  cause_id: string;
  cause_name: string;
  component_name: string;
  occurrence_count: number;
  total_downtime_hours: number;
  approx_mtbf_hours: number;
  risk_level: 'High' | 'Moderate' | 'Low';
}

export interface SubgraphData {
  nodes: any[];
  edges: any[];
  total_nodes: number;
  total_edges: number;
}
