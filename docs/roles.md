# Orchestrator role templates (five fixed roles)

Locked 2026-11-06 (task S-05). LangGraph provides **role orchestration only** — every specialist node is a
deterministic function; no hosted model anywhere, and **no model may override a policy decision**.

Pipeline (request path for `POST /api/v1/runs`, tasks.md §2.1):

```
Inventory → Path Finder → Injection Tester → Policy Verifier → Evidence Writer
```

Field names below use the `snake_case` contract vocabulary from `contract/CONTRACT.md` / §2.8
(`PathStatus`, `Basis`, `TrustLevel`, `Purpose`, `RuleId`, …). All messages are typed (Pydantic on the
backend); unknown fields are rejected.

---

## 1. Inventory — `InventoryRequest` → `InventoryReport`

**Responsibilities:** load the tool manifest, identities, grant matrix, policy rules, and the seeded
untrusted document from fixtures only; compute `input_digest` (sha256 of canonical JSON of
manifest+identities+grants+policy+doc); assemble the `ScenarioResponse` payload.

- `InventoryRequest` fields: `scenario_id: string`
- `InventoryReport` fields: `manifest.tools[]`, `identities[]`, `grants[]`, `policy{rules[]}`,
  `document{id, trust_level, content_is_data, content}`, `sensitive_sinks[]`, `input_digest`

**Must not:** call any tool; perform any network I/O; parse document content as instructions; label anything
verified (inventory is descriptive only).

## 2. Path Finder — `PathFindRequest` → `PathFindReport`

**Responsibilities:** build the NetworkX graph (`graph.nodes[]`, `graph.edges[]` with `source_ids`
`src:manifest` / `src:grant-matrix` / `src:policy-rule-*`); enumerate bounded simple paths from the
untrusted source to each `sensitive_sink`; label every found path **`candidate`** with
`basis: "graph_reachability"` and **no `reasons[]`**.

- `PathFindRequest` fields: `graph: Graph`, `origin: Id`, `sinks: Id[]`, `max_hops: int`
- `PathFindReport` fields: `paths[]` (each with `path_id`, `status: "candidate"`, `basis`, `origin`,
  `sink`, `hops[]`, `history[]`)

**Must not:** assign `allowed` / `blocked` / `disproved` (only the Policy Verifier does); label a candidate
path confirmed; read document content beyond structure; exceed the hop bound.

## 3. Injection Tester — `ReplayRequest` → `ReplayReport`

**Responsibilities:** replay each candidate hop through the mock tools (one policy check per hop), tracking
taint (`taint_labels`, `trust_level`); produce `replay_events[]` with redacted `input_preview` and
`input_digest` per event.

- `ReplayRequest` fields: `paths[]` (candidates), `tools` (mock boundary handle), `document`
- `ReplayReport` fields: `replay_events[]` (`event_id`, `seq`, `actor`, `tool`, `decision`, `executed`,
  `trust_level`, `purpose`, `taint_labels[]`, `source_ids[]`, `input_digest`, `input_preview`,
  `policy`, `tool_result`)

**Must not:** execute any tool whose decision is not `allowed` (`executed` stays `false`); ever produce
`executed: true` for `finance.export`; render or forward untrusted content raw (preview is redacted);
treat embedded document text as instructions.

## 4. Policy Verifier — `VerifyRequest` → `VerifyReport`

**Responsibilities:** re-verify every hop with the deterministic rule engine (ADR-0001) and assign the
final path status: `allowed` / `blocked` (with non-empty `reasons[]`, each `rule_id ∈ {R1,R2,R3}`) /
`disproved` (no grant edge at all). Records `history[]` transitions (`candidate → blocked`, …).

- `VerifyRequest` fields: `paths[]`, `replay_events[]`, `policy{rules[]}`, `grants[]`
- `VerifyReport` fields: `paths[]` with final `status`/`basis: "policy_verifier"`/`reasons[]`/`rule_refs[]`,
  per-event `policy{decision, rule_ids[], reasons[]}`

**Must not:** call a model, an LLM, or any stochastic component — **this role wraps a pure function
(`evaluate(call_ctx, policy, grants) -> PolicyDecision`); no model may override it**; default-deny on any
uncertainty; invent reason codes outside the rule tables.

## 5. Evidence Writer — `EvidenceRequest` → `EvidenceReport`

**Responsibilities:** append hash-chained evidence records (`evidence_id`, `kind`, `run_id`,
`captured_at`, `source_id`, `summary`, `hash`, `prev_hash`, `trace{path_ids[], event_ids[]}`); persist the
run, events, and pending approval items; assemble the final `RunResponse` (summary counts, `policy_diff`
with `simulated: true`, `recommendation`, `retests` RT-1..RT-3, `approval`).

- `EvidenceRequest` fields: `run_id`, `scenario_id`, `graph`, `paths[]`, `replay_events[]`,
  `policy_diff`, `recommendation`, `retests[]`
- `EvidenceReport` fields: the complete `RunResponse` (identical output for identical input except
  `run_id` / `generated_at`)

**Must not:** include free-form instruction fields in evidence; mutate or delete evidence (append-only,
hash-chained); mark any approval item `applied: true` or `simulated: false` (the queue records decisions
only — never applies policy, never calls a tool); write the simulated policy diff to disk.
