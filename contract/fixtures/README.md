# Contract fixtures

Hand-authored golden fixtures for the `demo-v1` scenario. Provenance: **hand-authored during Wave 0
(task S-03)** from the contract in `contract/openapi.yaml` / `contract/CONTRACT.md`; they are validated
against `contract/schemas/*.json` by `scripts/validate_fixtures.py` (runnable without the backend).
They will be **replaced by actual backend output in task BE-12**, which compares generated runs against
these files in tests only (the backend never reads them at runtime).

- `demo_scenario.json` — the `ScenarioResponse` for `GET /api/v1/scenarios/demo`:
  exactly 4 tools, 2 identities, the full grant matrix (incl. the marked vestigial
  `document_assistant → finance.lookup` over-grant), exactly 3 rules (`R1`, `R2`, `R3`),
  the seeded untrusted document with `content_is_data: true` and `trust_level: "untrusted"`,
  and `sensitive_sinks: ["tool:finance.export"]`.
- `run.demo.json` — a complete golden `RunResponse` for `POST /api/v1/runs` (`scenario_id: demo-v1`):
  all five demo paths `P1`–`P5` (P1/P2 `blocked`, P3/P5 `allowed`, P4 `disproved`), replay events
  `evt:0001`–`evt:0006` (zero `executed: true` for `finance.export`), the simulated `policy-v2-simulated`
  diff, recommendation `REC-1`, retests `RT-1`–`RT-3` (RT-2 `allowed`), a pending approval item
  (`applied: false`, `simulated: true`), and 7 hash-chained evidence records with `source_id`s.

The frontend renders these files directly (fixture-first adapter) with no backend running.
