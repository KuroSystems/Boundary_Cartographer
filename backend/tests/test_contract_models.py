"""BE-01 acceptance tests: typed models match the frozen contract schemas.

- model_json_schema() for RunResponse/ScenarioResponse is diffed against
  contract/schemas/*.json: required fields and enums must match exactly
  (extra-field drift fails).
- Enum values are asserted identical to the contract's closed enums.
- Model validators enforce the contract invariants (candidate/blocked/executed/approval).
- The golden fixtures (contract/fixtures/*.json) validate against the models.
"""

import json
from pathlib import Path as FsPath

import pytest
from pydantic import ValidationError

from app.contracts import (
    ApprovalItem,
    ApprovalState,
    ApprovalStatus,
    Basis,
    Decision,
    Path,
    PathStatus,
    PolicyDecision,
    ReplayEvent,
    ReplayPolicyVerdict,
    RuleId,
    RunResponse,
    ScenarioResponse,
)

ROOT = FsPath(__file__).resolve().parents[2]
RUN_SCHEMA = json.loads((ROOT / "contract/schemas/run_response.schema.json").read_text())
SCENARIO_SCHEMA = json.loads((ROOT / "contract/schemas/scenario_response.schema.json").read_text())
RUN_FIXTURE = json.loads((ROOT / "contract/fixtures/run.demo.json").read_text())
SCENARIO_FIXTURE = json.loads((ROOT / "contract/fixtures/demo_scenario.json").read_text())


# ---------------------------------------------------------------- helpers
def _resolve(root: dict, node: dict) -> dict:
    """Resolve a local $ref chain against the given schema root."""
    seen = 0
    while isinstance(node, dict) and "$ref" in node and seen < 50:
        ref = node["$ref"]
        assert ref.startswith("#/"), f"only local refs supported, got {ref}"
        target = root
        for part in ref[2:].split("/"):
            target = target[part]
        node = target
        seen += 1
    return node


def _diff(c_root: dict, m_root: dict, c_node: dict, m_node: dict, path: str, errors: list) -> None:
    c_node = _resolve(c_root, c_node)
    m_node = _resolve(m_root, m_node)
    if "properties" in c_node:
        c_props = c_node["properties"]
        m_props = m_node.get("properties", {})
        c_req = set(c_node.get("required", []))
        m_req = set(m_node.get("required", []))
        if c_req != m_req:
            errors.append(
                f"{path}: required mismatch contract={sorted(c_req)} model={sorted(m_req)}"
            )
        if m_node.get("additionalProperties") is not False:
            errors.append(f"{path}: model object missing additionalProperties: false")
        for name, c_sub in c_props.items():
            if name in m_props:
                _diff(c_root, m_root, c_sub, m_props[name], f"{path}.{name}", errors)
            else:
                errors.append(f"{path}: contract property {name!r} missing in model schema")
    if "enum" in c_node:
        # model enums may appear as enum, as anyOf[...enum] (Optional[X]), or as const (Literal)
        candidates = []
        if "enum" in m_node:
            candidates.append(m_node["enum"])
        for sub in m_node.get("anyOf", []):
            sub = _resolve(m_root, sub)
            if isinstance(sub, dict) and "enum" in sub:
                candidates.append(sub["enum"])
        if "const" in m_node:
            candidates.append([m_node["const"]])
        if not any(set(c) == set(c_node["enum"]) for c in candidates):
            errors.append(f"{path}: enum mismatch contract={c_node['enum']} model={candidates}")
    if c_node.get("type") == "array" and "items" in c_node:
        _diff(c_root, m_root, c_node["items"], m_node.get("items", {}), f"{path}[]", errors)
    if isinstance(c_node.get("additionalProperties"), dict):
        _diff(
            c_root, m_root, c_node["additionalProperties"],
            m_node.get("additionalProperties", {}), f"{path}{{}}", errors,
        )


def _assert_schema_matches(model, contract_schema: dict) -> None:
    model_schema = model.model_json_schema(by_alias=True)
    errors: list[str] = []
    _diff(contract_schema, model_schema, contract_schema, model_schema, model.__name__, errors)
    assert not errors, "model schema drifted from contract:\n" + "\n".join(errors)


# ---------------------------------------------------------------- tests
def test_run_response_model_schema_matches_contract():
    _assert_schema_matches(RunResponse, RUN_SCHEMA)


def test_scenario_response_model_schema_matches_contract():
    _assert_schema_matches(ScenarioResponse, SCENARIO_SCHEMA)


def test_enum_values_match_contract_exactly():
    contract_enums = {
        "PathStatus": {"candidate", "allowed", "blocked", "disproved"},
        "Basis": {"graph_reachability", "policy_verifier"},
        "Decision": {"allowed", "blocked", "not_executed"},
        "TrustLevel": {"trusted", "untrusted", "derived_untrusted", "mixed"},
    }
    assert {e.value for e in PathStatus} == contract_enums["PathStatus"]
    assert {e.value for e in Basis} == contract_enums["Basis"]
    assert {e.value for e in Decision} == contract_enums["Decision"]
    from app.contracts import TrustLevel

    assert {e.value for e in TrustLevel} == contract_enums["TrustLevel"]
    # spot-check remaining closed enums against the contract document
    from app.contracts import (
        ApprovalStatus,
        AuthBasis,
        ChangeOp,
        EdgeKind,
        EvidenceKind,
        NodeKind,
        Purpose,
        RuleId,
    )

    assert {e.value for e in ApprovalStatus} == {"pending", "approved", "rejected"}
    assert {e.value for e in AuthBasis} == {
        "user_request", "policy_grant", "human_approval", "system_default", "untrusted_content",
    }
    assert {e.value for e in ChangeOp} == {
        "revoke_grant", "add_guard", "drop_inheritance", "modify",
    }
    assert {e.value for e in EdgeKind} == {
        "flows_to", "may_invoke", "reads", "produces", "derived_from", "delegates_to",
    }
    assert {e.value for e in EvidenceKind} == {
        "source", "manifest", "grant", "policy_rule", "event",
    }
    assert {e.value for e in NodeKind} == {"source", "identity", "tool", "data_scope", "output"}
    assert {e.value for e in Purpose} == {"document_summarization", "finance_reporting"}
    assert {e.value for e in RuleId} == {"R1", "R2", "R3"}


def test_golden_run_fixture_validates_against_model():
    run = RunResponse.model_validate(RUN_FIXTURE)
    assert run.scenario_id == "demo-v1"
    assert {p.path_id for p in run.paths} == {"P1", "P2", "P3", "P4", "P5"}
    rt2 = [r for r in run.retests if r.retest_id == "RT-2"]
    assert rt2 and rt2[0].actual == PathStatus.ALLOWED


def test_golden_scenario_fixture_validates_against_model():
    scenario = ScenarioResponse.model_validate(SCENARIO_FIXTURE)
    assert len(scenario.manifest.tools) == 4
    assert len(scenario.identities) == 2
    assert [r.id for r in scenario.policy.rules] == [RuleId.R1, RuleId.R2, RuleId.R3]
    assert scenario.document.content_is_data is True
    assert scenario.sensitive_sinks == ["tool:finance.export"]


def test_extra_fields_are_forbidden():
    with pytest.raises(ValidationError):
        RunResponse.model_validate({**RUN_FIXTURE, "unexpected_field": 1})


def _minimal_path(**overrides) -> dict:
    base = {
        "path_id": "P9",
        "status": "candidate",
        "basis": "graph_reachability",
        "origin": "source:x",
        "sink": "tool:y",
        "hops": [],
        "rule_refs": [],
        "reasons": [],
        "history": [],
    }
    base.update(overrides)
    return base


def test_candidate_path_must_have_graph_reachability_basis_and_no_reasons():
    with pytest.raises(ValidationError):
        Path.model_validate(_minimal_path(basis="policy_verifier"))
    with pytest.raises(ValidationError):
        Path.model_validate(
            _minimal_path(
                reasons=[{
                    "code": "R2_CROSS_PURPOSE_FLOW", "rule_id": "R2",
                    "message": "m", "evidence_ids": [],
                }]
            )
        )


def test_blocked_path_must_have_reasons():
    with pytest.raises(ValidationError):
        Path.model_validate(_minimal_path(status="blocked", basis="policy_verifier"))


def _minimal_event(**overrides) -> dict:
    base = {
        "event_id": "evt:9999",
        "seq": 1,
        "actor": "document_assistant",
        "tool": "finance.export",
        "decision": "blocked",
        "executed": True,
        "trust_level": "derived_untrusted",
        "purpose": "document_summarization",
        "taint_labels": ["untrusted_document"],
        "source_ids": ["src:doc-untrusted-001"],
        "input_digest": "sha256:" + "a" * 64,
        "input_preview": "scope=<redacted>",
        "policy": {"decision": "deny", "rule_ids": ["R3"], "reasons": []},
        "tool_result": None,
    }
    base.update(overrides)
    return base


def test_non_allowed_decision_must_not_be_executed():
    with pytest.raises(ValidationError):
        ReplayEvent.model_validate(_minimal_event())
    # allowed + executed is fine
    ReplayEvent.model_validate(_minimal_event(decision="allowed", executed=True))


def test_approval_item_must_be_records_only():
    item = {
        "approval_id": "ap-1",
        "subject": {"type": "recommendation", "id": "REC-1"},
        "status": "pending",
        "requested_at": "2026-11-06T10:00:00Z",
        "decided_by": None,
        "decided_at": None,
        "note": None,
        "applied": True,
        "simulated": True,
        "effect": "records a decision only",
    }
    with pytest.raises(ValidationError):
        ApprovalItem.model_validate(item)
    item["applied"] = False
    ApprovalItem.model_validate(item)


def test_run_response_rejects_executed_finance_export():
    fixture = json.loads(json.dumps(RUN_FIXTURE))
    fixture["replay_events"][3]["executed"] = True  # evt:0004 is finance.export
    fixture["replay_events"][3]["decision"] = "allowed"
    with pytest.raises(ValidationError):
        RunResponse.model_validate(fixture)


def test_policy_verdict_deny_shape():
    verdict = ReplayPolicyVerdict(
        decision=PolicyDecision.DENY, rule_ids=[RuleId.R2], reasons=[]
    )
    assert verdict.decision == "deny"


def test_approval_state_roundtrip_from_fixture():
    state = ApprovalState.model_validate(RUN_FIXTURE["approval"])
    assert state.status == ApprovalStatus.PENDING
    assert all(i.applied is False and i.simulated is True for i in state.items)
