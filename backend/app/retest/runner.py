"""Retest runner (BE-10): RT-1/RT-2/RT-3 replayed through replay + verifier
against the simulated policy (policy-v2-simulated).
"""

from app.contracts import Path, PathStatus
from app.fixtures import LoadedFixtures
from app.policy.engine import Policy
from app.replay import replay_path

RT_DEFS = [
    ("RT-1", "injection chain P1/P2 against policy-v2-simulated", ["P1", "P2"], "blocked"),
    ("RT-2", "legitimate document summarization (P3)", ["P3"], "allowed"),
    ("RT-3", "legitimate finance report (P5, finance_reporting + approval)",
     ["P5"], "allowed"),
]


def _path_status_after_replay(path: Path, fixtures: LoadedFixtures, policy: Policy,
                              drop_inheritance: bool, approvals) -> str:
    events = replay_path(path, fixtures, policy=policy, approvals=approvals,
                         drop_inheritance=drop_inheritance)
    if any(e.decision == "blocked" for e in events):
        return PathStatus.BLOCKED.value
    if any(e.decision == "allowed" for e in events):
        return PathStatus.ALLOWED.value
    return PathStatus.CANDIDATE.value


def run_retests(paths_by_id: dict[str, Path], fixtures: LoadedFixtures, policy: Policy,
               changes: list[dict], approvals=None) -> list[dict]:
    """Run the fixed retest set against the simulated policy. Returns Retest payloads."""
    drop_inheritance = any(c["op"] == "drop_inheritance" for c in changes)
    results = []
    for rt_id, name, path_ids, expected in RT_DEFS:
        actuals = {
            _path_status_after_replay(paths_by_id[pid], fixtures, policy,
                                      drop_inheritance, approvals)
            for pid in path_ids
        }
        actual = actuals.pop() if len(actuals) == 1 else "failed"
        evidence = [f"evt:retest-{rt_id.lower()}-{pid.lower()}" for pid in path_ids]
        results.append({
            "retest_id": rt_id,
            "name": name,
            "expected": expected,
            "actual": actual,
            "passed": actual == expected,
            "evidence_ids": evidence,
        })
    return results
