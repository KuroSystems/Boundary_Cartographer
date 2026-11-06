// Zod mirrors of the frozen contract (FE-02). Objects are .strict() so unknown
// fields are rejected (additionalProperties: false). The seven contract
// invariants from contract/CONTRACT.md §4 are asserted in superRefine.
//
// Status string literals are NOT written here — the enums come from the const
// arrays in types.ts (the only hand-written literals, enforced by a grep test).

import { z } from 'zod';
import {
  APPROVAL_STATUSES,
  BASIS_GRAPH_REACHABILITY,
  STATUS_ALLOWED,
  STATUS_BLOCKED,
  STATUS_CANDIDATE,
  CHANGE_OPS,
  EDGE_KINDS,
  EVIDENCE_KINDS,
  NODE_KINDS,
  NODE_RISKS,
  PATH_BASES,
  PATH_STATUSES,
  POLICY_DECISIONS,
  PURPOSES,
  REPLAY_DECISIONS,
  RETEST_IDS,
  RULE_IDS,
  RUN_STATUSES,
  TRUST_LEVELS,
} from './types';

const zPathStatus = z.enum(PATH_STATUSES);
const zRuleId = z.enum(RULE_IDS);

// ---------------------------------------------------------------- scenario
const toolManifestEntrySchema = z.strictObject({
  name: z.string(),
  description: z.string(),
  required_scopes: z.array(z.string()),
  purposes: z.array(z.enum(PURPOSES)),
  sensitive: z.boolean(),
  approval_required: z.boolean(),
});

const identityEntrySchema = z.strictObject({
  id: z.string(),
  label: z.string(),
  allowed_purposes: z.array(z.enum(PURPOSES)),
  may_delegate_to: z.array(z.string()),
});

const grantEntrySchema = z.strictObject({
  identity: z.string(),
  tool: z.string(),
  scopes: z.array(z.string()),
  purposes: z.array(z.enum(PURPOSES)),
  note: z.string().optional(),
});

const policyRuleMetaSchema = z.strictObject({
  id: zRuleId,
  name: z.string(),
  summary: z.string(),
  effect: z.string().optional(),
  reason_codes: z.array(z.string()).optional(),
});

const policyMetaSchema = z.strictObject({
  policy_id: z.string(),
  engine: z.string(),
  rules: z.array(policyRuleMetaSchema),
});

const seededDocumentSchema = z.strictObject({
  id: z.string(),
  title: z.string(),
  trust_level: z.enum(TRUST_LEVELS),
  content_is_data: z.boolean(),
  content: z.string(),
  source_ids: z.array(z.string()),
});

export const scenarioResponseSchema = z.strictObject({
  schema_version: z.string(),
  scenario_id: z.string(),
  name: z.string(),
  manifest: z.strictObject({ tools: z.array(toolManifestEntrySchema) }),
  identities: z.array(identityEntrySchema),
  grants: z.array(grantEntrySchema),
  policy: policyMetaSchema,
  document: seededDocumentSchema,
  sensitive_sinks: z.array(z.string()),
});

export type ScenarioSourceIds = Set<string>;

export function scenarioSourceIds(scenario: z.infer<typeof scenarioResponseSchema>): ScenarioSourceIds {
  return new Set([
    ...scenario.document.source_ids,
    ...scenario.document.id ? [scenario.document.id] : [],
    'src:manifest',
    'src:grant-matrix',
    ...scenario.policy.rules.map((r) => `src:policy-rule-${r.id.slice(1).toLowerCase()}`),
  ]);
}

// ---------------------------------------------------------------- run pieces
const pathHopSchema = z.strictObject({
  step: z.number(),
  from: z.string(),
  to: z.string(),
  kind: z.enum(EDGE_KINDS),
  actor: z.string(),
  purpose: z.enum(PURPOSES),
});

const pathReasonSchema = z.strictObject({
  code: z.string(),
  rule_id: zRuleId,
  message: z.string(),
  evidence_ids: z.array(z.string()),
});

const pathSchema = z.strictObject({
  path_id: z.string(),
  status: zPathStatus,
  basis: z.enum(PATH_BASES),
  origin: z.string(),
  sink: z.string(),
  stated_purpose: z.enum(PURPOSES).optional(),
  tainted: z.boolean().optional(),
  hops: z.array(pathHopSchema),
  rule_refs: z.array(zRuleId),
  reasons: z.array(pathReasonSchema),
  history: z.array(
    z.strictObject({ status: zPathStatus, at_step: z.string() }),
  ),
});

const replayPolicyVerdictSchema = z.strictObject({
  decision: z.enum(POLICY_DECISIONS),
  rule_ids: z.array(zRuleId),
  reasons: z.array(pathReasonSchema),
});

const replayEventSchema = z.strictObject({
  event_id: z.string(),
  seq: z.number(),
  actor: z.string(),
  tool: z.string(),
  decision: z.enum(REPLAY_DECISIONS),
  executed: z.boolean(),
  trust_level: z.enum(TRUST_LEVELS),
  purpose: z.enum(PURPOSES),
  taint_labels: z.array(z.string()),
  source_ids: z.array(z.string()),
  input_digest: z.string(),
  input_preview: z.string(),
  policy: replayPolicyVerdictSchema,
  tool_result: z.unknown().nullable(),
});

const graphNodeSchema = z.strictObject({
  id: z.string(),
  kind: z.enum(NODE_KINDS),
  label: z.string(),
  risk: z.enum(NODE_RISKS).optional(),
  scopes: z.array(z.string()).optional(),
  source_ids: z.array(z.string()),
});

const graphEdgeSchema = z.strictObject({
  id: z.string(),
  from: z.string(),
  to: z.string(),
  kind: z.enum(EDGE_KINDS),
  purposes: z.array(z.enum(PURPOSES)).optional(),
  scopes: z.array(z.string()).optional(),
  trust: z.enum(TRUST_LEVELS).optional(),
  source_ids: z.array(z.string()),
});

const snapshotRuleSchema = z.strictObject({ id: zRuleId, summary: z.string() });
const snapshotGrantSchema = z.strictObject({
  identity: z.string(),
  tool: z.string(),
  scopes: z.array(z.string()),
});
const policySnapshotSchema = z.strictObject({
  policy_id: z.string(),
  rules: z.array(snapshotRuleSchema),
  grants: z.array(snapshotGrantSchema),
});

const policyDiffChangeSchema = z.strictObject({
  op: z.enum(CHANGE_OPS),
  target: z.string(),
  rule_id: zRuleId,
  summary: z.string(),
});

const policyDiffSchema = z.strictObject({
  simulated: z.boolean(),
  before: policySnapshotSchema,
  after: policySnapshotSchema,
  changes: z.array(policyDiffChangeSchema),
});

const recommendationChangeSchema = z.strictObject({
  change_id: z.string(),
  op: z.enum(CHANGE_OPS),
  target: z.string(),
  rule_refs: z.array(zRuleId),
});

const recommendationSchema = z.strictObject({
  recommendation_id: z.string(),
  title: z.string(),
  changes: z.array(recommendationChangeSchema),
  expected_effect: z.record(zPathStatus),
  risk_if_unchanged: z.string(),
  generated_from: z.array(zRuleId),
});

const retestSchema = z.strictObject({
  retest_id: z.enum(RETEST_IDS),
  name: z.string(),
  expected: zPathStatus,
  actual: zPathStatus,
  passed: z.boolean(),
  evidence_ids: z.array(z.string()),
});

const approvalItemSchema = z.strictObject({
  approval_id: z.string(),
  subject: z.strictObject({
    type: z.enum(['recommendation', 'policy_change']),
    id: z.string(),
  }),
  status: z.enum(APPROVAL_STATUSES),
  requested_at: z.string(),
  decided_by: z.string().nullable(),
  decided_at: z.string().nullable(),
  note: z.string().nullable(),
  applied: z.boolean(),
  simulated: z.boolean(),
  effect: z.string(),
});

const approvalStateSchema = z.strictObject({
  status: z.enum(APPROVAL_STATUSES),
  items: z.array(approvalItemSchema),
});

const evidenceRecordSchema = z.strictObject({
  evidence_id: z.string(),
  kind: z.enum(EVIDENCE_KINDS),
  run_id: z.string(),
  captured_at: z.string(),
  source_id: z.string(),
  summary: z.string(),
  hash: z.string(),
  prev_hash: z.string().nullable(),
  trace: z.strictObject({
    path_ids: z.array(z.string()),
    event_ids: z.array(z.string()),
  }),
});

// ---------------------------------------------------------------- run + invariants
const baseRunResponseSchema = z.strictObject({
  schema_version: z.string(),
  run_id: z.string(),
  scenario_id: z.string(),
  status: z.enum(RUN_STATUSES),
  deterministic: z.boolean(),
  generated_at: z.string(),
  input_digest: z.string(),
  engine: z.strictObject({
    policy_engine: z.string(),
    orchestrator: z.string(),
  }),
  summary: z.strictObject({
    headline: z.string(),
    counts: z.strictObject({
      nodes: z.number(),
      edges: z.number(),
      candidate_paths: z.number(),
      allowed_paths: z.number(),
      blocked_paths: z.number(),
      disproved_paths: z.number(),
    }),
    sensitive_sinks: z.array(z.string()),
    tools_tested: z.number(),
    identities: z.number(),
    rules: z.number(),
  }),
  graph: z.strictObject({
    nodes: z.array(graphNodeSchema),
    edges: z.array(graphEdgeSchema),
  }),
  paths: z.array(pathSchema),
  replay_events: z.array(replayEventSchema),
  policy_diff: policyDiffSchema,
  recommendation: recommendationSchema,
  retests: z.array(retestSchema),
  approval: approvalStateSchema,
  evidence: z.array(evidenceRecordSchema),
});

/**
 * RunResponse with the seven contract invariants (CONTRACT.md §4) asserted in
 * superRefine. When `sourceIds` (from the scenario fixture) is provided,
 * invariant 5 additionally checks every evidence source_id resolves there.
 */
export function runResponseSchemaFor(sourceIds?: ScenarioSourceIds) {
  return baseRunResponseSchema.superRefine((run, ctx) => {
    const add = (path: (string | number)[], message: string) =>
      ctx.addIssue({ code: z.ZodIssueCode.custom, path, message });

    for (const p of run.paths) {
      // (1) candidate ⇒ no reasons, basis graph_reachability
      if (p.status === STATUS_CANDIDATE) {
        if (p.reasons.length > 0) add(['paths', p.path_id, 'reasons'], 'candidate path must have no reasons');
        if (p.basis !== BASIS_GRAPH_REACHABILITY)
          add(['paths', p.path_id, 'basis'], 'candidate path basis must be graph_reachability');
      }
      // (2) blocked ⇒ non-empty reasons, every reason rule_id ∈ {R1,R2,R3}
      if (p.status === STATUS_BLOCKED) {
        if (p.reasons.length === 0) add(['paths', p.path_id, 'reasons'], 'blocked path must have reasons');
        for (const r of p.reasons) {
          if (!RULE_IDS.includes(r.rule_id)) {
            add(['paths', p.path_id, 'reasons'], `reason rule_id ${r.rule_id} not in ${RULE_IDS.join(',')}`);
          }
        }
      }
    }

    for (const e of run.replay_events) {
      // (3) executed == false for decision != allowed; finance.export never executed
      if (e.decision !== STATUS_ALLOWED && e.executed !== false) {
        add(['replay_events', e.event_id], `decision ${e.decision} must have executed == false`);
      }
      if (e.tool === 'finance.export' && e.executed === true) {
        add(['replay_events', e.event_id], 'finance.export must never have executed == true');
      }
    }

    // (4) approval items: applied == false, simulated == true always
    for (const item of run.approval.items) {
      if (item.applied !== false) add(['approval', item.approval_id, 'applied'], 'applied must always be false');
      if (item.simulated !== true) add(['approval', item.approval_id, 'simulated'], 'simulated must always be true');
    }

    // (5) evidence source_id present and resolvable in the scenario fixture
    for (const rec of run.evidence) {
      if (!rec.source_id) add(['evidence', rec.evidence_id, 'source_id'], 'source_id must be present');
      else if (sourceIds && !sourceIds.has(rec.source_id)) {
        add(['evidence', rec.evidence_id, 'source_id'], `source_id ${rec.source_id} not resolvable in scenario fixture`);
      }
    }

    // (6) retests always contain RT-2 with actual allowed
    const rt2 = run.retests.find((r) => r.retest_id === 'RT-2');
    if (!rt2) add(['retests'], 'retests must contain RT-2');
    else if (rt2.actual !== STATUS_ALLOWED) add(['retests', 'RT-2', 'actual'], 'RT-2 actual must be allowed');

    // (7) policy_diff.simulated == true
    if (run.policy_diff.simulated !== true) {
      add(['policy_diff', 'simulated'], 'policy_diff.simulated must be true');
    }
  });
}

/** Default run schema (invariants 1–4, 6, 7; #5 needs the scenario for source resolution). */
export const runResponseSchema = runResponseSchemaFor();
