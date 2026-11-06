"""BE-07 evaluator tests: determinism, purity (no network/random/clock imports),
precedence R1 > R3 > R2, default-deny behaviour, and the false-positive guard."""

import ast
from pathlib import Path

from app.contracts import ApprovalStatus, AuthBasis, Purpose
from app.policy import ApprovalRef, CallContext, evaluate, load_policy

POLICY_PKG = Path(__file__).resolve().parents[1] / "app" / "policy"
BANNED_IMPORTS = {"socket", "random", "time", "datetime", "requests", "httpx",
                  "urllib", "subprocess", "os.system"}

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


def test_finance_export_with_r1_basis_denied_even_if_rest_valid():
    """Core injection assertion: untrusted purpose origin denies finance.export
    even when identity, purpose value, and approval are all valid."""
    decision = evaluate(ctx(
        actor="finance_analyst", tool="finance.export", purpose=FR,
        purpose_origin=UC, args_taint=False,
        approval=ApprovalRef(approval_id="ap-1", status=ApprovalStatus.APPROVED,
                             origin=AuthBasis.HUMAN_APPROVAL),
    ))
    assert decision.decision == "deny"
    assert decision.primary_reason.code == "R1_INSTRUCTION_NOT_AUTHORIZATION"
    assert "R1" in decision.rule_ids


def test_untrusted_approval_origin_always_denies():
    decision = evaluate(ctx(
        actor="finance_analyst", tool="finance.export", purpose=FR,
        purpose_origin=AuthBasis.USER_REQUEST, args_taint=False,
        approval=ApprovalRef(approval_id="CFO-2026-11", status=ApprovalStatus.APPROVED,
                             origin=UC),
    ))
    assert decision.decision == "deny"
    assert decision.primary_reason.rule_id == "R1"


def test_precedence_r1_over_r3_over_r2():
    # triggers R1 (untrusted purpose origin), R3 (wrong purpose), R2 (tainted)
    decision = evaluate(ctx(
        actor="finance_analyst", tool="finance.export", purpose=DS, purpose_origin=UC,
        args_taint=True, taint_labels=["untrusted_document"],
    ))
    assert decision.decision == "deny"
    assert decision.primary_reason.rule_id == "R1"
    assert set(decision.rule_ids) == {"R1", "R3", "R2"}
    # order of findings follows precedence R1 > R3 > R2
    assert [f.rule_id for f in decision.findings] == sorted(
        [f.rule_id for f in decision.findings],
        key=lambda r: ["R1", "R3", "R2"].index(r),
    )


def test_false_positive_guard_legitimate_finance_call_allowed():
    decision = evaluate(ctx(
        actor="finance_analyst", tool="finance.export", purpose=FR,
        purpose_origin=AuthBasis.USER_REQUEST, args_taint=False,
        approval=ApprovalRef(approval_id="ap-1", status=ApprovalStatus.APPROVED,
                             origin=AuthBasis.HUMAN_APPROVAL),
    ))
    assert decision.decision == "allow"
    assert decision.findings == []


def test_legitimate_document_call_allowed():
    decision = evaluate(ctx(tool="document.summarize", purpose=DS, args_taint=True,
                            taint_labels=["untrusted_document"]))
    assert decision.decision == "allow"


def test_determinism_100_identical_evaluations():
    contexts = [
        ctx(),
        ctx(tool="finance.export", actor="finance_analyst", purpose=FR, purpose_origin=UC),
        ctx(tool="finance.lookup", purpose=DS, args_taint=True),
    ]
    for c in contexts:
        serials = {evaluate(c).model_dump_json() for _ in range(100)}
        assert len(serials) == 1


def test_policy_package_imports_no_network_random_or_clock():
    for path in sorted(POLICY_PKG.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in BANNED_IMPORTS, \
                        f"{path.name} imports banned module {alias.name}"
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in BANNED_IMPORTS, \
                    f"{path.name} imports banned module {node.module}"


def test_each_rules_reason_codes_covered_by_suite():
    policy = load_policy()
    covered = set()
    contexts = [
        ctx(purpose_origin=UC),
        ctx(tool="finance.export", actor="document_assistant"),
        ctx(tool="finance.export", actor="finance_analyst", purpose=DS),
        ctx(tool="finance.export", actor="finance_analyst", purpose=FR),
        ctx(tool="finance.export", actor="finance_analyst", purpose=FR, args_taint=True,
            approval=ApprovalRef(status=ApprovalStatus.APPROVED, origin=AuthBasis.HUMAN_APPROVAL)),
        ctx(tool="finance.lookup", purpose=DS, args_taint=True),
    ]
    for c in contexts:
        covered.update(f.code for f in evaluate(c, policy).findings)
    all_codes = {code for rule in policy.rules for code in rule["reason_codes"]}
    assert covered == all_codes


def test_policy_hash_stable():
    from app.policy import policy_hash

    p1, p2 = load_policy(), load_policy()
    assert policy_hash(p1) == policy_hash(p2)
    assert policy_hash(p1).startswith("sha256:")
    assert p1.rule_ids == ["R1", "R2", "R3"]
