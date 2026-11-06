# Boundary Cartographer — API/Data Contract (v1)

> **Locked by: BE/FE, 2026-11-06** · **Contract version: 1.0.0** · Frozen at the end of Wave 0 (task S-02).
> Machine-readable artifacts: `contract/openapi.yaml`, `contract/schemas/run_response.schema.json`,
> `contract/schemas/scenario_response.schema.json`, `contract/CHANGELOG.md`.
> The backend also serves this contract at `/api/v1/openapi.json`; contract tests assert it equals the file.

## 1. Conventions

- Base path `/api/v1`. All request/response bodies are `application/json`.
- All field names are `snake_case`.
- Every object schema sets `additionalProperties: false` — **unknown fields are rejected** (JSON Schema) and by
  Pydantic (`extra="forbid"`) on the backend, and by Zod (`.strict()`) on the frontend.
- All enums are **closed** (see §5).
- Errors use the envelope in §3 with HTTP `400`/`404`/`409`/`422`.
- Runs are **synchronous by contract**; there is no streaming, polling, or WebSocket.
- The API is fully offline after bootstrap: no outbound calls, no hosted models on the authorization path.

## 2. Endpoints

| Method | Path | Purpose | Success | Errors |
| --- | --- | --- | --- | --- |
| `GET` | `/api/v1/health` | Liveness for scripts | `200` `HealthResponse` | — |
| `GET` | `/api/v1/scenarios/demo` | Demo scenario: tool inventory, identities, grant matrix, policy metadata, seeded document. No run, no side effects, safe to call repeatedly. | `200` `ScenarioResponse` | — |
| `POST` | `/api/v1/runs` | Run the offline analysis synchronously. Body `{"scenario_id":"demo-v1","options":{"include_disproved":true}}`. | `201` `RunResponse` | `400 SCENARIO_NOT_FOUND`, `422 VALIDATION_ERROR` |
| `GET` | `/api/v1/runs/{run_id}` | Retrieve a completed run. | `200` `RunResponse` | `404 RUN_NOT_FOUND` |
| `POST` | `/api/v1/runs/{run_id}/approval` | Record `approve`/`reject` on the run's approval queue. **Records a decision only** (§6). | `200` `ApprovalState` | `400 INVALID_DECISION`, `404 RUN_NOT_FOUND`, `409 APPROVAL_ALREADY_DECIDED`, `422 VALIDATION_ERROR` |

### Request/response payloads

- `HealthResponse`: `{"status":"ok","offline":true,"policy_engine":"local-rule-engine@1.0.0"}`
- `CreateRunRequest`: `{scenario_id: string, options: {include_disproved: boolean}}`
- `ApprovalDecisionRequest`: `{approval_id: string, decision: "approve"|"reject", decided_by: string|null, note: string|null}`
- `ScenarioResponse`: see `contract/schemas/scenario_response.schema.json` — exactly 4 tools, 2 identities,
  the full grant matrix, exactly 3 rules (`R1`,`R2`,`R3`), the seeded document with `content_is_data: true` and
  `trust_level: "untrusted"`, and `sensitive_sinks: ["tool:finance.export"]`.
- `RunResponse`: see `contract/schemas/run_response.schema.json` — the single source of truth shared by both lanes.

## 3. Error envelope

```json
{ "error": { "code": "<UPPER_SNAKE>", "message": "<short>", "details": {} } }
```

Closed `code` enum: `SCENARIO_NOT_FOUND`, `RUN_NOT_FOUND`, `APPROVAL_ALREADY_DECIDED`, `INVALID_DECISION`,
`VALIDATION_ERROR`. HTTP mapping: `400` (bad request / unknown scenario / invalid decision), `404` (unknown run),
`409` (approval already decided), `422` (body failed schema validation).

## 4. Contract invariants (asserted by BE-12 and FE-02, both sides)

- `paths[].status == "candidate"` ⇒ no `reasons[]`, `basis == "graph_reachability"`.
- `paths[].status == "blocked"` ⇒ `reasons[]` non-empty and every reason has a `rule_id` ∈ `{R1,R2,R3}`.
- `replay_events[].executed == false` for every `decision != "allowed"`; `finance.export` has **no** event with
  `executed == true`.
- `approval.items[].applied == false` and `simulated == true` always.
- `evidence[].source_id` is always present and resolvable in the scenario fixture.
- `retests[]` always contains `RT-2` with `actual == "allowed"`.
- `policy_diff.simulated == true`.
- Field names are `snake_case`; unknown fields are rejected (`additionalProperties: false`) in JSON Schema.

## 5. Closed enums (identical strings on both lanes)

| Field | Values |
| --- | --- |
| run `status` | `completed`, `failed` |
| path `status` | `candidate`, `allowed`, `blocked`, `disproved` |
| path `basis` | `graph_reachability`, `policy_verifier` |
| replay event `decision` | `allowed`, `blocked`, `not_executed` |
| policy verdict `decision` | `allow`, `deny` |
| `trust_level` | `trusted`, `untrusted`, `derived_untrusted`, `mixed` |
| node `kind` | `source`, `identity`, `tool`, `data_scope`, `output` |
| edge `kind` | `flows_to`, `may_invoke`, `reads`, `produces`, `derived_from`, `delegates_to` |
| evidence `kind` | `source`, `manifest`, `grant`, `policy_rule`, `event` |
| `purpose` | `document_summarization`, `finance_reporting` |
| authorization `basis` (provenance) | `user_request`, `policy_grant`, `human_approval`, `system_default`, `untrusted_content` — **never sufficient; always rejected** |
| `rule_id` | `R1`, `R2`, `R3` |
| `approval.status` / approval item `status` | `pending`, `approved`, `rejected` |
| approval request `decision` | `approve`, `reject` |
| diff/recommendation `op` | `revoke_grant`, `add_guard`, `drop_inheritance`, `modify` |
| node `risk` | `low`, `medium`, `high`, `critical` |
| error `code` | `SCENARIO_NOT_FOUND`, `RUN_NOT_FOUND`, `APPROVAL_ALREADY_DECIDED`, `INVALID_DECISION`, `VALIDATION_ERROR` |
| retest `retest_id` | `RT-1`, `RT-2`, `RT-3` |

## 6. Semantics that are part of the contract (not implementation details)

- **Candidate paths are never labelled confirmed.** Only the deterministic policy verifier assigns
  `allowed` / `blocked` / `disproved`. `candidate` always has `basis: "graph_reachability"` and no `reasons[]`.
- **The approval queue records a decision only.** `POST /api/v1/runs/{run_id}/approval` never applies policy,
  never calls a tool, never mutates anything except the recorded decision (`applied: false`, `simulated: true`
  on every item, always). A repeat decision on a decided item is `409 APPROVAL_ALREADY_DECIDED`.
- **Untrusted document content is data.** It is never parsed as instructions, never rendered as HTML, never used
  to set purpose, identity, permissions, or approval. `input_preview` in replay events is redacted.
- **Determinism.** Identical input ⇒ identical `RunResponse` except `run_id` / `generated_at`. `deterministic` is
  always `true`. `input_digest` is the sha256 of canonical JSON of scenario + policy + grants.
- **Evidence** is append-only, hash-chained (`hash`, `prev_hash`), and every record carries a `source_id`
  resolvable in the scenario fixture. No free-form instruction fields exist anywhere in the payloads.
- **The demo scope is frozen**: exactly 4 tools, 2 identities, 1 seeded untrusted document, 3 rules, one
  sensitive sink (`tool:finance.export`).

## 7. Field-by-field notes for `RunResponse` (top level)

| Field | Type | Notes |
| --- | --- | --- |
| `schema_version` | semver string | `1.0.0`; additive changes bump MINOR (§8). |
| `run_id` | string | Unique per run; the only field besides `generated_at` allowed to differ across identical runs. |
| `scenario_id` | string | Echoes the request, e.g. `demo-v1`. |
| `status` | `completed` \| `failed` | Runs are synchronous; `failed` is reserved for internal errors. |
| `deterministic` | boolean | Always `true`. |
| `generated_at` | RFC 3339 date-time | Wall clock is allowed **here only**; never on the authorization path. |
| `input_digest` | `sha256:<64 hex>` | Hash of scenario + policy + grants (canonical JSON). |
| `engine` | `{policy_engine, orchestrator}` | e.g. `local-rule-engine@1.0.0`, `langgraph@<ver>`. Authorization never depends on an LLM. |
| `summary` | object | `headline`, `counts{nodes,edges,candidate_paths,allowed_paths,blocked_paths,disproved_paths}`, `sensitive_sinks`, `tools_tested`, `identities`, `rules`. |
| `graph` | `{nodes[], edges[]}` | Node kinds/edge kinds per §5; every node/edge carries `source_ids` (`src:manifest`, `src:grant-matrix`, `src:policy-rule-*`). |
| `paths[]` | array | `P1`–`P5` in the demo. `hops[]` ordered by `step`; `reasons[]` required when `blocked`; `history[]` documents `candidate → blocked` transitions. |
| `replay_events[]` | array | One per replayed hop, `seq` ordered; `executed` false unless `decision == "allowed"`; `tool_result` null otherwise. |
| `policy_diff` | object | `simulated: true` always; `before`/`after` are `PolicySnapshot`s; `changes[]` use closed `op` enum. Computed in memory, never written to disk. |
| `recommendation` | object | `REC-1` in the demo; `changes[]` map to rule IDs; `expected_effect` maps path IDs to expected statuses. |
| `retests[]` | exactly 3 | Fixed set `RT-1`, `RT-2`, `RT-3`; `RT-2` (legitimate summarization) must be `allowed`. |
| `approval` | object | `status` + `items[]`; items are always `applied: false`, `simulated: true`. |
| `evidence[]` | array | Hash-chained records with `source_id`, `hash`, `prev_hash`, `trace{path_ids, event_ids}`. |

## 8. Versioning / change protocol

- `schema_version` = `MAJOR.MINOR.PATCH`; additive changes = MINOR, breaking = MAJOR.
- After Wave 0 the contract is **frozen**. Any change requires:
  1. agreement from both contributors (BE and FE lanes),
  2. schema + fixture + generated types updated **in the same commit**,
  3. both lanes re-run their contract tests.
- `S-03` (fixtures) is the only task allowed to add fields without a change request.
- Every change is recorded in `contract/CHANGELOG.md`.

## 9. Frontend contract types

- Generated from `contract/openapi.yaml` via `npm run codegen:types` → `frontend/src/api/generated.ts`
  (committed, so runtime stays offline).
- Hand-shaped mirrors in `frontend/src/api/types.ts`; runtime validation with Zod (`.strict()`,
  `additionalProperties` rejected) in `frontend/src/api/schemas.ts`.
- Import rule: the backend never imports frontend code or reads `run.demo.json` at runtime; `BE-12` may
  *compare* against the golden fixture in tests only.
