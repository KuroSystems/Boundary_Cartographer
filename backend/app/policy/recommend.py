"""REC-1 least-privilege recommendation, generated from verifier findings (BE-10, §2.7).

The recommendation text is derived from typed findings (reason codes + rule
IDs) — no free-text field is required to render it. Changes are emitted in
deterministic order C1, C2, C3.
"""

from dataclasses import dataclass

from app.contracts import ChangeOp, RuleId


@dataclass(frozen=True)
class RecChangeSpec:
    change_id: str
    op: ChangeOp
    target: str
    rule_refs: tuple[RuleId, ...]
    source_codes: tuple[str, ...]  # findings that trigger this change


# Deterministic order (tasks.md §2.7).
CHANGE_SPECS = [
    RecChangeSpec(
        "C1", ChangeOp.REVOKE_GRANT, "document_assistant:finance.lookup",
        (RuleId.R2,), ("R2_CROSS_PURPOSE_FLOW",),
    ),
    RecChangeSpec(
        "C2", ChangeOp.ADD_GUARD, "finance.export:taint=no_untrusted",
        (RuleId.R3,), ("R3_TAINTED_ARGS", "R3_NO_VALID_APPROVAL"),
    ),
    RecChangeSpec(
        "C3", ChangeOp.DROP_INHERITANCE, "delegation:document_assistant->finance_analyst",
        (RuleId.R1,), ("R1_INSTRUCTION_NOT_AUTHORIZATION", "R3_WRONG_PURPOSE"),
    ),
]


def build_recommendation(findings: list[dict]) -> dict:
    """Build the REC-1 payload from verifier findings.

    `findings`: list of {"code": str, "rule_id": str, "path_id": str} collected
    from blocked paths' reasons. Only changes backed by an observed finding
    are emitted.
    """
    codes = {f["code"] for f in findings}
    changes = []
    for spec in CHANGE_SPECS:
        if codes & set(spec.source_codes):
            changes.append({
                "change_id": spec.change_id,
                "op": spec.op.value,
                "target": spec.target,
                "rule_refs": [r.value for r in spec.rule_refs],
            })
    return {
        "recommendation_id": "REC-1",
        "title": "Narrow finance reachability from document workflows",
        "changes": changes,
        "expected_effect": {"P1": "blocked", "P2": "blocked", "P3": "allowed", "P5": "allowed"},
        "risk_if_unchanged": "untrusted document content can reach finance scopes via delegation",
        "generated_from": ["R1", "R2", "R3"],
    }
