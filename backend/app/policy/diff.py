"""In-memory policy diff (BE-10): deep-copy policy-v1, apply REC-1 changes,
emit policy-v2-simulated. Nothing is ever written to disk — the diff is
computed in memory and `simulated` is always true.
"""

import copy

from app.policy.engine import Policy


def apply_changes(policy: Policy, changes: list[dict]) -> Policy:
    """Return a NEW Policy with the changes applied in memory (input untouched)."""
    rules = copy.deepcopy([dict(r) for r in policy.rules])
    for change in changes:
        op, target = change["op"], change["target"]
        if op == "revoke_grant":
            continue  # grants live in the snapshot, handled by build_policy_diff
        if op == "add_guard" and target.startswith("finance.export"):
            for rule in rules:
                if rule["id"] == "R3":
                    cond = rule.setdefault("conditions", {})
                    cond.setdefault("require", {})["taint"] = "no_untrusted"
                    guards = rule.setdefault("guards", [])
                    if "taint:no_untrusted" not in guards:
                        guards.append("taint:no_untrusted")
        elif op == "drop_inheritance":
            for rule in rules:
                if rule["id"] == "R1":
                    cond = rule.setdefault("conditions", {})
                    cond["delegation_purpose_inheritance"] = "forbidden"
    base = policy.policy_id[: -len("-v1")] if policy.policy_id.endswith("-v1") else policy.policy_id
    return Policy(
        policy_id=base + "-v2-simulated",
        engine=policy.engine,
        rules=tuple(rules),
    )


def _snapshot(policy: Policy, grants: list[dict]) -> dict:
    return {
        "policy_id": policy.policy_id,
        "rules": [{"id": r["id"], "summary": r["summary"]} for r in policy.rules],
        "grants": [{"identity": g["identity"], "tool": g["tool"], "scopes": list(g["scopes"])}
                   for g in grants],
    }


def build_policy_diff(policy: Policy, changes: list[dict], grants: list[dict]) -> dict:
    """Build the typed PolicyDiff payload (simulated=True, never persisted)."""
    after = apply_changes(policy, changes)
    after_grants = list(grants)
    for change in changes:
        if change["op"] == "revoke_grant":
            identity, tool = change["target"].split(":")
            after_grants = [
                g for g in after_grants
                if not (g["identity"] == identity and g["tool"] == tool)
            ]
    return {
        "simulated": True,
        "before": _snapshot(policy, grants),
        "after": _snapshot(after, after_grants),
        "changes": [
            {
                "op": c["op"],
                "target": c["target"],
                "rule_id": c["rule_refs"][0],
                "summary": _change_summary(c),
            }
            for c in changes
        ],
    }


def _change_summary(change: dict) -> str:
    return {
        "revoke_grant": "revoke vestigial over-grant",
        "add_guard": "bind finance.export with an explicit taint: no_untrusted guard",
        "drop_inheritance": "delegated context must re-establish purpose from a trusted request",
        "modify": "modify rule",
    }.get(change["op"], "change")
