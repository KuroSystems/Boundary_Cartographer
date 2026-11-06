# Contract changelog

All notable changes to the Boundary Cartographer API/data contract (`contract/openapi.yaml`,
`contract/schemas/*.json`). Format follows the change protocol in `contract/CONTRACT.md` §8.

## 1.0.0 — 2026-11-06 (locked by BE/FE)

Initial frozen contract, published at the end of Wave 0 (task S-02):

- Endpoints: `GET /api/v1/health`, `GET /api/v1/scenarios/demo`, `POST /api/v1/runs`,
  `GET /api/v1/runs/{run_id}`, `POST /api/v1/runs/{run_id}/approval`.
- Error envelope `{"error": {code, message, details}}` with closed code enum
  (`SCENARIO_NOT_FOUND`, `RUN_NOT_FOUND`, `APPROVAL_ALREADY_DECIDED`, `INVALID_DECISION`, `VALIDATION_ERROR`).
- `RunResponse` and `ScenarioResponse` published as OpenAPI 3.1 components and as standalone
  JSON Schema (draft 2020-12) files under `contract/schemas/`; all object schemas use
  `additionalProperties: false`; all enums closed (see CONTRACT.md §5).
- All seven contract invariants recorded verbatim in CONTRACT.md §4.
- Approval queue semantics: records a decision only — never applies policy, never calls a tool.
