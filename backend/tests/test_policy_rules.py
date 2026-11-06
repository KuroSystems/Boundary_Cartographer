"""BE-07 rule tests: table-driven, >=4 positive and >=3 negative cases per rule,
all using real reason codes from the frozen policy fixture."""

import pytest

from app.contracts import ApprovalStatus, AuthBasis, Purpose
from app.policy import ApprovalRef, CallContext, rule_r1, rule_r2, rule_r3

DS = Purpose.DOCUMENT_SUMMARIZATION
FR = Purpose.FINANCE_REPORTING
UC = AuthBasis.UNTRUSTED_CONTENT


def ctx(**overrides) -> CallContext:
    base = {
        "actor": "document_assistant",
        "tool": "document.summarize",
        "purpose": DS,
        "purpose_origin": AuthBasis.USER_REQUEST,
        "args_taint": False,
        "taint_labels": [],
        "approval": None,
        "delegation_chain": [],
    }
    base.update(overrides)
    return CallContext(**base)


# ---------------------------------------------------------------- R1
R1_POSITIVE = [
    {"purpose_origin": UC},                                              # purpose from injection
    {"approval": ApprovalRef(
        approval_id="CFO-2026-11", status=ApprovalStatus.APPROVED, origin=UC)},
    {"purpose_origin": UC, "tool": "finance.export", "actor": "finance_analyst",
     "purpose": FR,
     "approval": ApprovalRef(status=ApprovalStatus.APPROVED, origin=AuthBasis.HUMAN_APPROVAL)},
    {"purpose_origin": UC, "delegation_chain": ["document_assistant", "finance_analyst"]},
]
R1_NEGATIVE = [
    {"purpose_origin": AuthBasis.USER_REQUEST},
    {"purpose_origin": AuthBasis.POLICY_GRANT},
    {"approval": ApprovalRef(status=ApprovalStatus.APPROVED, origin=AuthBasis.HUMAN_APPROVAL)},
    {"purpose_origin": AuthBasis.SYSTEM_DEFAULT, "approval": None},
]


@pytest.mark.parametrize("overrides", R1_POSITIVE)
def test_r1_fires(overrides):
    findings = rule_r1(ctx(**overrides))
    assert findings and all(f.rule_id == "R1" for f in findings)
    assert all(f.code == "R1_INSTRUCTION_NOT_AUTHORIZATION" for f in findings)


@pytest.mark.parametrize("overrides", R1_NEGATIVE)
def test_r1_silent(overrides):
    assert rule_r1(ctx(**overrides)) == []


# ---------------------------------------------------------------- R2
R2_POSITIVE = [
    {"purpose": DS, "tool": "finance.lookup", "args_taint": True,
     "taint_labels": ["untrusted_document"]},
    {"purpose": DS, "tool": "finance.export", "args_taint": True,
     "taint_labels": ["untrusted_document"]},
    {"purpose": DS, "tool": "finance.export", "args_taint": True, "actor": "finance_analyst",
     "delegation_chain": ["document_assistant", "finance_analyst"]},
    {"purpose": DS, "tool": "finance.lookup", "args_taint": True, "actor": "finance_analyst"},
]
R2_NEGATIVE = [
    {"purpose": DS, "tool": "document.summarize", "args_taint": True},   # doc workflow, doc tool
    {"purpose": FR, "tool": "finance.lookup", "args_taint": True},       # finance workflow
    {"purpose": DS, "tool": "finance.lookup", "args_taint": False},      # untainted args
    {"purpose": DS, "tool": "finance.export", "args_taint": False},
]


@pytest.mark.parametrize("overrides", R2_POSITIVE)
def test_r2_fires(overrides):
    findings = rule_r2(ctx(**overrides))
    assert len(findings) == 1
    assert findings[0].rule_id == "R2"
    assert findings[0].code == "R2_CROSS_PURPOSE_FLOW"


@pytest.mark.parametrize("overrides", R2_NEGATIVE)
def test_r2_silent(overrides):
    assert rule_r2(ctx(**overrides)) == []


# ---------------------------------------------------------------- R3
R3_POSITIVE = [
    {"tool": "finance.export", "actor": "document_assistant"},          # wrong identity
    {"tool": "finance.export", "actor": "finance_analyst", "purpose": DS},  # wrong purpose
    {"tool": "finance.export", "actor": "finance_analyst", "purpose": FR},  # no approval
    {"tool": "finance.export", "actor": "finance_analyst", "purpose": FR,
     "args_taint": True},  # tainted args
    {"tool": "finance.export", "actor": "finance_analyst", "purpose": FR,
     "approval": ApprovalRef(status=ApprovalStatus.REJECTED, origin=AuthBasis.HUMAN_APPROVAL)},
]
R3_NEGATIVE = [
    {"tool": "finance.lookup", "actor": "document_assistant"},           # R3 only governs export
    {"tool": "document.summarize", "actor": "document_assistant", "purpose": DS},
    {"tool": "finance.export", "actor": "finance_analyst", "purpose": FR, "args_taint": False,
     "approval": ApprovalRef(approval_id="ap-1", status=ApprovalStatus.APPROVED,
                             origin=AuthBasis.HUMAN_APPROVAL)},
]


@pytest.mark.parametrize("overrides", R3_POSITIVE)
def test_r3_fires(overrides):
    findings = rule_r3(ctx(**overrides))
    assert findings and all(f.rule_id == "R3" for f in findings)
    assert all(f.code in {"R3_WRONG_IDENTITY", "R3_WRONG_PURPOSE", "R3_NO_VALID_APPROVAL",
                          "R3_TAINTED_ARGS"} for f in findings)


@pytest.mark.parametrize("overrides", R3_NEGATIVE)
def test_r3_silent(overrides):
    assert rule_r3(ctx(**overrides)) == []


def test_r3_reason_codes_all_reachable():
    cases = {
        "R3_WRONG_IDENTITY": {"tool": "finance.export", "actor": "document_assistant"},
        "R3_WRONG_PURPOSE": {"tool": "finance.export", "actor": "finance_analyst", "purpose": DS},
        "R3_NO_VALID_APPROVAL": {"tool": "finance.export", "actor": "finance_analyst",
                                 "purpose": FR},
        "R3_TAINTED_ARGS": {"tool": "finance.export", "actor": "finance_analyst", "purpose": FR,
                            "args_taint": True,
                            "approval": ApprovalRef(status=ApprovalStatus.APPROVED,
                                                    origin=AuthBasis.HUMAN_APPROVAL)},
    }
    seen = set()
    for overrides in cases.values():
        seen.update(f.code for f in rule_r3(ctx(**overrides)))
    assert seen == set(cases)
