// Contract types (FE-02). The codegen output in generated.ts is the source of
// truth; this module re-exports it and defines the narrow unions/const arrays
// — the ONLY place status string literals are written by hand (a grep test in
// schemas.test.ts enforces this).

import type { components } from './generated';

type Schemas = components['schemas'];

// ---- re-exported contract types ----
export type RunResponse = Schemas['RunResponse'];
export type ScenarioResponse = Schemas['ScenarioResponse'];
export type HealthResponse = Schemas['HealthResponse'];
export type Path = Schemas['Path'];
export type PathHop = Schemas['PathHop'];
export type PathReason = Schemas['PathReason'];
export type PathHistoryEntry = Schemas['PathHistoryEntry'];
export type ReplayEvent = Schemas['ReplayEvent'];
export type ReplayPolicyVerdict = Schemas['ReplayPolicyVerdict'];
export type Graph = Schemas['Graph'];
export type GraphNode = Schemas['GraphNode'];
export type GraphEdge = Schemas['GraphEdge'];
export type Summary = Schemas['Summary'];
export type SummaryCounts = Schemas['Summary']['counts'];
export type PolicyDiff = Schemas['PolicyDiff'];
export type PolicyDiffChange = Schemas['PolicyDiffChange'];
export type Recommendation = Schemas['Recommendation'];
export type Retest = Schemas['Retest'];
export type ApprovalState = Schemas['ApprovalState'];
export type ApprovalItem = Schemas['ApprovalItem'];
export type ApprovalDecisionRequest = Schemas['ApprovalDecisionRequest'];
export type EvidenceRecord = Schemas['EvidenceRecord'];

// ---- narrow unions (status literals live here and only here) ----
export const RUN_STATUSES = ['completed', 'failed'] as const;
export type RunStatus = (typeof RUN_STATUSES)[number];

export const PATH_STATUSES = ['candidate', 'allowed', 'blocked', 'disproved'] as const;
export type PathStatus = (typeof PATH_STATUSES)[number];

export const REPLAY_DECISIONS = ['allowed', 'blocked', 'not_executed'] as const;
export type ReplayDecision = (typeof REPLAY_DECISIONS)[number];

export const POLICY_DECISIONS = ['allow', 'deny'] as const;
export type PolicyDecision = (typeof POLICY_DECISIONS)[number];

export const RULE_IDS = ['R1', 'R2', 'R3'] as const;
export type RuleId = (typeof RULE_IDS)[number];

export const CHANGE_OPS = ['revoke_grant', 'add_guard', 'drop_inheritance', 'modify'] as const;
export type ChangeOp = (typeof CHANGE_OPS)[number];

export const APPROVAL_STATUSES = ['pending', 'approved', 'rejected'] as const;
export type ApprovalStatus = (typeof APPROVAL_STATUSES)[number];

export const RETEST_IDS = ['RT-1', 'RT-2', 'RT-3'] as const;
export type RetestId = (typeof RETEST_IDS)[number];

export const EVIDENCE_KINDS = ['source', 'manifest', 'grant', 'policy_rule', 'event'] as const;
export type EvidenceKind = (typeof EVIDENCE_KINDS)[number];

export const NODE_KINDS = ['source', 'identity', 'tool', 'data_scope', 'output'] as const;
export type NodeKind = (typeof NODE_KINDS)[number];

export const EDGE_KINDS = [
  'flows_to',
  'may_invoke',
  'reads',
  'produces',
  'derived_from',
  'delegates_to',
] as const;
export type EdgeKind = (typeof EDGE_KINDS)[number];

export const TRUST_LEVELS = ['trusted', 'untrusted', 'derived_untrusted', 'mixed'] as const;
export type TrustLevel = (typeof TRUST_LEVELS)[number];

export const PATH_BASES = ['graph_reachability', 'policy_verifier'] as const;
export type PathBasis = (typeof PATH_BASES)[number];

// Named status constants — use these instead of bare literals anywhere else.
export const STATUS_CANDIDATE: PathStatus = 'candidate';
export const STATUS_ALLOWED: PathStatus = 'allowed';
export const STATUS_BLOCKED: PathStatus = 'blocked';
export const STATUS_DISPROVED: PathStatus = 'disproved';
export const BASIS_GRAPH_REACHABILITY: PathBasis = 'graph_reachability';

export const PURPOSES = ['document_summarization', 'finance_reporting'] as const;
export type Purpose = (typeof PURPOSES)[number];

export const NODE_RISKS = ['low', 'medium', 'high', 'critical'] as const;
export type NodeRisk = (typeof NODE_RISKS)[number];

// Map a replay decision to its pill style. Literals live here only.
export const DECISION_TO_PILL: Record<string, PathStatus> = {
  allowed: 'allowed',
  blocked: 'blocked',
  not_executed: 'disproved',
};
