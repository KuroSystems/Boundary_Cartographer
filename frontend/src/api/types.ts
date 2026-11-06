// Contract-shaped types for the API adapter seam (FE-01).
// Structural subsets of contract/openapi.yaml; FE-02 replaces these with
// openapi-typescript codegen + Zod validation.

export interface HealthResponse {
  status: 'ok';
  offline: boolean;
  policy_engine: string;
}

export interface ToolEntry {
  name: string;
  description: string;
  required_scopes: string[];
  purposes: string[];
  sensitive: boolean;
  approval_required: boolean;
}

export interface IdentityEntry {
  id: string;
  label: string;
  allowed_purposes: string[];
  may_delegate_to: string[];
}

export interface GrantEntry {
  identity: string;
  tool: string;
  scopes: string[];
  purposes: string[];
  note?: string;
}

export interface PolicyRuleMeta {
  id: string;
  name: string;
  summary: string;
}

export interface PolicyMeta {
  policy_id: string;
  engine: string;
  rules: PolicyRuleMeta[];
}

export interface SeededDocument {
  id: string;
  title: string;
  trust_level: string;
  content_is_data: boolean;
  content: string;
}

export interface ScenarioResponse {
  schema_version: string;
  scenario_id: string;
  name: string;
  manifest: { tools: ToolEntry[] };
  identities: IdentityEntry[];
  grants: GrantEntry[];
  policy: PolicyMeta;
  document: SeededDocument;
  sensitive_sinks: string[];
}

export type PathStatus = 'candidate' | 'allowed' | 'blocked' | 'disproved';

export interface PathHop {
  step: number;
  tool: string;
  actor: string;
  purpose: string;
}

export interface PathReason {
  code: string;
  rule_id: string;
  message: string;
  evidence_ids: string[];
}

export interface Path {
  path_id: string;
  status: PathStatus;
  basis: string;
  hops: PathHop[];
  reasons: PathReason[];
  rule_refs: string[];
}

export interface ReplayPolicyVerdict {
  decision: 'allow' | 'deny';
  rule_ids: string[];
  reasons: PathReason[];
}

export interface ReplayEvent {
  event_id: string;
  tool: string;
  actor: string;
  purpose: string;
  decision: 'allowed' | 'blocked' | 'not_executed';
  executed: boolean;
  trust_level: string;
  taint_labels: string[];
  policy: ReplayPolicyVerdict;
  input_preview: string;
  source_ids: string[];
}

export interface GraphNode {
  id: string;
  kind: string;
  label: string;
  risk?: 'low' | 'medium' | 'high' | 'critical';
  scopes?: string[];
  source_ids: string[];
}

export interface GraphEdge {
  id: string;
  from: string;
  to: string;
  kind: string;
  trust?: string;
  purposes?: string[];
  scopes?: string[];
  source_ids: string[];
}

export interface Graph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface SummaryCounts {
  nodes: number;
  edges: number;
  candidate_paths: number;
  allowed_paths: number;
  blocked_paths: number;
  disproved_paths: number;
}

export interface Summary {
  headline: string;
  counts: SummaryCounts;
  sensitive_sinks: string[];
  tools_tested: number;
  identities: number;
  rules: number;
}

export interface PolicySnapshotRef {
  policy_id: string;
  rules: PolicyRuleMeta[];
  grants: GrantEntry[];
}

export interface PolicyDiffChange {
  change_id: string;
  op: 'revoke_grant' | 'add_guard' | 'drop_inheritance' | 'modify';
  target: string;
  summary: string;
}

export interface PolicyDiff {
  before: PolicySnapshotRef;
  after: PolicySnapshotRef;
  changes: PolicyDiffChange[];
  simulated: boolean;
}

export interface RecommendationChange {
  change_id: string;
  op: string;
  target: string;
  summary: string;
}

export interface Recommendation {
  recommendation_id: string;
  changes: RecommendationChange[];
  generated_from: string[];
}

export interface Retest {
  retest_id: string;
  name: string;
  path_ids: string[];
  expected: string;
  actual: string;
  passed: boolean;
  evidence_ids: string[];
}

export interface ApprovalItem {
  approval_id: string;
  subject: { type: string; id: string };
  status: 'pending' | 'approved' | 'rejected';
  requested_at: string;
  decided_by: string | null;
  decided_at: string | null;
  note: string | null;
  applied: boolean;
  simulated: boolean;
  effect: string;
}

export interface ApprovalState {
  status: 'pending' | 'approved' | 'rejected';
  items: ApprovalItem[];
}

export interface ApprovalDecisionRequest {
  approval_id: string;
  decision: 'approve' | 'reject';
  decided_by?: string | null;
  note?: string | null;
}

export interface EvidenceRecord {
  evidence_id: string;
  kind: string;
  run_id: string;
  captured_at: string;
  source_id: string;
  summary: string;
  hash: string;
  prev_hash: string | null;
  trace: { path_ids: string[]; event_ids: string[] };
}

export interface RunResponse {
  schema_version: string;
  run_id: string;
  scenario_id: string;
  status: 'completed' | 'failed';
  deterministic: boolean;
  generated_at: string;
  input_digest: string;
  engine: { policy_engine: string; orchestrator: string };
  summary: Summary;
  graph: Graph;
  paths: Path[];
  replay_events: ReplayEvent[];
  policy_diff: PolicyDiff;
  recommendation: Recommendation;
  retests: Retest[];
  approval: ApprovalState;
  evidence: EvidenceRecord[];
}
