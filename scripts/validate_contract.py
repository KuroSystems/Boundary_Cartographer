"""Validate the frozen API contract artifacts (task S-02, wired into `make verify`).

Checks:
  1. contract/openapi.yaml parses as YAML and validates as an OpenAPI 3.1 document
     (openapi-spec-validator).
  2. contract/schemas/run_response.schema.json and scenario_response.schema.json are valid
     JSON and valid JSON Schema draft 2020-12 (jsonschema meta-validation).
  3. Every object schema in the OpenAPI document sets additionalProperties: false.
  4. The closed enums required by the contract (status, basis, decision, trust_level, kind,
     op, approval.status) are present and closed.

Runs fully offline. Exit 0 on success, 1 with a printed report on failure.
"""

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate

ROOT = Path(__file__).resolve().parent.parent
OPENAPI = ROOT / "contract" / "openapi.yaml"
SCHEMAS = [
    ROOT / "contract" / "schemas" / "run_response.schema.json",
    ROOT / "contract" / "schemas" / "scenario_response.schema.json",
]

REQUIRED_ENUMS = {
    "RunStatus": {"completed", "failed"},
    "PathStatus": {"candidate", "allowed", "blocked", "disproved"},
    "Basis": {"graph_reachability", "policy_verifier"},
    "ReplayDecision": {"allowed", "blocked", "not_executed"},
    "TrustLevel": {"trusted", "untrusted", "derived_untrusted", "mixed"},
    "NodeKind": {"source", "identity", "tool", "data_scope", "output"},
    "EdgeKind": {"flows_to", "may_invoke", "reads", "produces", "derived_from", "delegates_to"},
    "ApprovalStatus": {"pending", "approved", "rejected"},
    "ChangeOp": {"revoke_grant", "add_guard", "drop_inheritance", "modify"},
    "ErrorCode": {
        "SCENARIO_NOT_FOUND",
        "RUN_NOT_FOUND",
        "APPROVAL_ALREADY_DECIDED",
        "INVALID_DECISION",
        "VALIDATION_ERROR",
    },
}


def check_openapi(spec: dict) -> list[str]:
    errors: list[str] = []
    validate(spec)  # raises on invalid OpenAPI
    schemas = spec["components"]["schemas"]

    def walk(node, path):
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                if node.get("additionalProperties") is not False:
                    errors.append(f"object schema at {path} missing additionalProperties: false")
                for key, sub in node["properties"].items():
                    walk(sub, f"{path}.{key}")
            for key, sub in node.items():
                if key in ("items",):
                    walk(sub, f"{path}[]")
        elif isinstance(node, list):
            for i, sub in enumerate(node):
                walk(sub, f"{path}[{i}]")

    for name, schema in schemas.items():
        walk(schema, f"components.schemas.{name}")

    for name, expected in REQUIRED_ENUMS.items():
        if name not in schemas:
            errors.append(f"missing required enum schema {name}")
            continue
        actual = set(schemas[name].get("enum", []))
        if actual != expected:
            errors.append(f"enum {name}: expected {sorted(expected)}, got {sorted(actual)}")
    return errors


def main() -> int:
    failures: list[str] = []

    spec = yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))
    try:
        failures += check_openapi(spec)
        print("PASS openapi.yaml validates as OpenAPI", spec["openapi"])
    except Exception as exc:  # noqa: BLE001 - report any validator error
        failures.append(f"openapi.yaml invalid: {exc}")

    for schema_path in SCHEMAS:
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            print(f"PASS {schema_path.name} is valid JSON Schema draft 2020-12")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{schema_path.name}: {exc}")

    if failures:
        print("\nFAIL contract validation:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nAll contract checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
