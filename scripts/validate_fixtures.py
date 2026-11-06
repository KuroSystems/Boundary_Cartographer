"""Validate the hand-authored contract fixtures (task S-03, wired into `make verify`).

Runs without the backend (uses only jsonschema + stdlib). Checks:
  1. `contract/fixtures/demo_scenario.json` validates against
     `contract/schemas/scenario_response.schema.json`.
  2. `contract/fixtures/run.demo.json` validates against
     `contract/schemas/run_response.schema.json`.
  3. Scope freeze: exactly 4 tools, exactly 2 identities, exactly 3 rules (R1, R2, R3).
  4. All seven contract invariants (contract/CONTRACT.md §4) hold in run.demo.json,
     including: zero `executed: true` events for finance.export, and RT-2 present and allowed.

Exit 0 with a PASS summary on success, 1 with a FAIL report otherwise.
"""

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SCENARIO = ROOT / "contract" / "fixtures" / "demo_scenario.json"
RUN = ROOT / "contract" / "fixtures" / "run.demo.json"
SCENARIO_SCHEMA = ROOT / "contract" / "schemas" / "scenario_response.schema.json"
RUN_SCHEMA = ROOT / "contract" / "schemas" / "run_response.schema.json"


def check_invariants(run: dict) -> list[str]:
    errors: list[str] = []
    valid_rule_ids = {"R1", "R2", "R3"}

    # 1. candidate ⇒ no reasons, basis == graph_reachability
    for path in run["paths"]:
        if path["status"] == "candidate":
            if path["reasons"]:
                errors.append(f"{path['path_id']}: candidate path must have no reasons[]")
            if path["basis"] != "graph_reachability":
                errors.append(f"{path['path_id']}: candidate path basis must be graph_reachability")
        # 2. blocked ⇒ reasons non-empty, rule_id in {R1,R2,R3}
        if path["status"] == "blocked":
            if not path["reasons"]:
                errors.append(f"{path['path_id']}: blocked path must have non-empty reasons[]")
            for reason in path["reasons"]:
                if reason["rule_id"] not in valid_rule_ids:
                    errors.append(f"{path['path_id']}: reason rule_id {reason['rule_id']} not in R1-R3")

    # 3. executed == false for decision != allowed; finance.export never executed
    for event in run["replay_events"]:
        if event["decision"] != "allowed" and event["executed"] is not False:
            errors.append(f"{event['event_id']}: decision {event['decision']} must have executed == false")
        if event["tool"] == "finance.export" and event["executed"] is True:
            errors.append(f"{event['event_id']}: finance.export must never have executed == true")

    # 4. approval items always applied == false and simulated == true
    for item in run["approval"]["items"]:
        if item["applied"] is not False or item["simulated"] is not True:
            errors.append(f"{item['approval_id']}: approval item must have applied == false and simulated == true")

    # 5. evidence[].source_id present (schema enforces presence); resolvable in scenario fixture
    scenario_ids = {
        scenario["document"]["id"],
        "src:manifest",
        "src:grant-matrix",
        *(f"src:policy-rule-{r['id'][-1].lower()}" for r in scenario["policy"]["rules"]),
    }
    for record in run["evidence"]:
        if record["source_id"] not in scenario_ids:
            errors.append(f"{record['evidence_id']}: source_id {record['source_id']} not resolvable in scenario fixture")

    # 6. retests always contain RT-2 with actual == allowed
    rt2 = [r for r in run["retests"] if r["retest_id"] == "RT-2"]
    if not rt2 or rt2[0]["actual"] != "allowed":
        errors.append("retests[] must contain RT-2 with actual == allowed")

    # 7. policy_diff.simulated == true
    if run["policy_diff"]["simulated"] is not True:
        errors.append("policy_diff.simulated must be true")

    return errors


SCENARIO_ID_SOURCE = "src:doc-untrusted-001"


def main() -> int:
    global scenario
    failures: list[str] = []

    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    run = json.loads(RUN.read_text(encoding="utf-8"))

    scenario_schema = json.loads(SCENARIO_SCHEMA.read_text(encoding="utf-8"))
    run_schema = json.loads(RUN_SCHEMA.read_text(encoding="utf-8"))

    for label, payload, schema in [
        ("demo_scenario.json", scenario, scenario_schema),
        ("run.demo.json", run, run_schema),
    ]:
        errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda e: list(e.path))
        for err in errors:
            failures.append(f"{label}: at {'/'.join(map(str, err.path)) or '<root>'}: {err.message}")
        if not errors:
            print(f"PASS {label} validates against {schema['title']}")

    # scope freeze counts
    tools = scenario["manifest"]["tools"]
    identities = scenario["identities"]
    rules = scenario["policy"]["rules"]
    if len(tools) != 4:
        failures.append(f"expected exactly 4 tools, got {len(tools)}")
    if len(identities) != 2:
        failures.append(f"expected exactly 2 identities, got {len(identities)}")
    if sorted(r["id"] for r in rules) != ["R1", "R2", "R3"]:
        failures.append(f"expected exactly rules R1,R2,R3, got {[r['id'] for r in rules]}")
    if failures == [] or all("tool" not in f and "ident" not in f and "R1" not in f for f in failures):
        print(f"PASS scope freeze: 4 tools, 2 identities, 3 rules (R1,R2,R3)")

    if scenario["document"]["content_is_data"] is not True:
        failures.append("seeded document must have content_is_data: true")
    if scenario["sensitive_sinks"] != ["tool:finance.export"]:
        failures.append("sensitive_sinks must be [\"tool:finance.export\"]")

    failures += check_invariants(run)
    export_executed = [e["event_id"] for e in run["replay_events"]
                       if e["tool"] == "finance.export" and e["executed"] is True]
    if not export_executed:
        print("PASS zero executed:true events for finance.export")
    rt2 = [r for r in run["retests"] if r["retest_id"] == "RT-2"]
    if rt2 and rt2[0]["actual"] == "allowed":
        print("PASS RT-2 present and allowed")
    if len(run["evidence"]) >= 6:
        print(f"PASS {len(run['evidence'])} evidence records (>= 6)")

    if failures:
        print("\nFAIL fixture validation:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nAll fixture checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
