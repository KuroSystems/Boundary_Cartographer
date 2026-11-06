"""Contract tests: live POST /runs vs frozen schema and golden fixture (BE-12).

- Live response validates against contract/schemas/run_response.schema.json.
- Live response equals contract/fixtures/run.demo.json modulo volatile values
  (run_id / generated_at / hash chain); any divergence prints a field-level diff.
- A deliberate extra field fails schema validation (additionalProperties: false).
"""

import copy
import json

import jsonschema

from tests.conftest import CONTRACT_DIR

VOLATILE_KEYS = {"run_id", "generated_at", "captured_at", "requested_at", "decided_at",
                 "hash", "prev_hash"}


def _schema() -> dict:
    return json.loads(
        (CONTRACT_DIR / "schemas" / "run_response.schema.json").read_text(encoding="utf-8")
    )


def _golden() -> dict:
    return json.loads((CONTRACT_DIR / "fixtures" / "run.demo.json").read_text(encoding="utf-8"))


def _normalize(obj):
    """Replace volatile values with stable placeholders, recursively."""
    if isinstance(obj, dict):
        return {k: ("<volatile>" if k in VOLATILE_KEYS else _normalize(v))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize(v) for v in obj]
    return obj


def _field_diff(a, b, path="") -> list[str]:
    """Human-readable field-level diff between two JSON structures."""
    out = []
    if type(a) is not type(b):
        return [f"{path}: type {type(a).__name__} != {type(b).__name__}"]
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"{path}.{k}: only in golden = {json.dumps(b[k])[:120]}")
            elif k not in b:
                out.append(f"{path}.{k}: only in live = {json.dumps(a[k])[:120]}")
            else:
                out.extend(_field_diff(a[k], b[k], f"{path}.{k}"))
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(f"{path}: list length {len(a)} (live) != {len(b)} (golden)")
        for i, (x, y) in enumerate(zip(a, b)):
            out.extend(_field_diff(x, y, f"{path}[{i}]"))
    elif a != b:
        out.append(f"{path}: {json.dumps(a)[:100]} != {json.dumps(b)[:100]}")
    return out


def test_live_run_validates_against_frozen_schema(client, run_factory):
    resp, _ = run_factory()
    assert resp.status_code == 201
    jsonschema.Draft202012Validator(_schema()).validate(resp.json())


def test_golden_run_matches_live_modulo_volatile_fields(client, run_factory):
    resp, _ = run_factory()
    live = _normalize(resp.json())
    golden = _normalize(_golden())
    diff = _field_diff(live, golden)
    assert not diff, "live run diverges from contract/fixtures/run.demo.json:\n" + "\n".join(diff)


def test_golden_fixture_itself_validates_against_schema():
    jsonschema.Draft202012Validator(_schema()).validate(_golden())


def test_deliberate_contract_drift_fails_schema(client, run_factory):
    resp, _ = run_factory()
    drifted = copy.deepcopy(resp.json())
    drifted["unexpected_extra_field"] = True
    errors = list(jsonschema.Draft202012Validator(_schema()).iter_errors(drifted))
    assert errors, "additionalProperties: false must reject an extra top-level field"
    assert any("unexpected_extra_field" in str(e) for e in errors)


def test_schema_forbids_additional_properties_at_top_level():
    schema = _schema()
    assert schema.get("additionalProperties") is False
