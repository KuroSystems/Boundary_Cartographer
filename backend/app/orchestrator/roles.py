"""Five deterministic role nodes (BE-09) — matching docs/roles.md.

Each node is a pure function over the orchestrator state: it parses the
previous role's typed message (Pydantic — malformed input raises), computes its
report, and returns a state update. No node calls an LLM or the network.
"""

import uuid
from datetime import datetime, timezone

from app.contracts import (
    ApprovalState,
    ApprovalStatus,
    AuthBasis,
    Basis,
    EvidenceRecord,
    Path,
    PathHistoryEntry,
    PathStatus,
    ReplayEvent,
    RunResponse,
    RunStatus,
    ScenarioResponse,
    Summary,
    SummaryCounts,
)
from app.fixtures import load_fixtures
from app.graph import build_graph, find_paths, serialize_graph
from app.orchestrator.messages import (
    EvidenceReport,
    InventoryReport,
    PathFindReport,
    ReplayReport,
    VerifyReport,
)
from app.policy import ApprovalRef, load_policy
from app.replay import replay_path
from app.store.repository import compute_hash

ROLE_NAMES = ["inventory", "path_finder", "injection_tester", "policy_verifier", "evidence_writer"]


def inventory_node(state: dict) -> dict:
    """Inventory: load + cross-validate fixtures, assemble ScenarioResponse."""
    from app.orchestrator.messages import InventoryRequest

    req = InventoryRequest.model_validate({"scenario_id": state["scenario_id"]})
    fixtures = load_fixtures()
    if fixtures.scenario_id != req.scenario_id:
        raise ValueError(f"scenario {req.scenario_id!r} not found")
    scenario = fixtures.scenario_response()
    report = InventoryReport(
        scenario=scenario.model_dump(by_alias=True, mode="json"),
        input_digest=fixtures.input_digest,
    )
    return {"inventory": report.model_dump(mode="json"), "fixtures_digest": fixtures.input_digest}


def path_finder_node(state: dict) -> dict:
    """Path Finder: build graph, enumerate golden paths (candidate/disproved)."""
    from app.orchestrator.messages import PathFindRequest

    inventory = InventoryReport.model_validate(state["inventory"])
    scenario = ScenarioResponse.model_validate(inventory.scenario)
    fixtures = load_fixtures()
    g = build_graph(fixtures)
    graph = serialize_graph(g)
    origin = f"source:{fixtures.document['id'].removeprefix('src:')}"
    req = PathFindRequest(
        graph=graph.model_dump(by_alias=True, mode="json"),
        origin=origin,
        sinks=scenario.sensitive_sinks,
    )
    paths = find_paths(g, fixtures)
    report = PathFindReport(paths=[p.model_dump(by_alias=True, mode="json") for p in paths])
    return {
        "path_find": report.model_dump(mode="json"),
        "graph": req.graph,
    }


def injection_tester_node(state: dict) -> dict:
    """Injection Tester: replay every candidate path through the mock tools."""
    from app.orchestrator.messages import ReplayRequest

    path_find = PathFindReport.model_validate(state["path_find"])
    req = ReplayRequest(paths=path_find.paths)
    fixtures = load_fixtures()
    policy = load_policy()
    # The legitimate finance workflow (P5) runs with a real queue approval.
    queue = [ApprovalRef(approval_id="ap-queue", status=ApprovalStatus.APPROVED,
                         origin=AuthBasis.HUMAN_APPROVAL)]
    events: list[ReplayEvent] = []
    path_event_map: dict[str, list[str]] = {}
    for raw in req.paths:
        path = Path.model_validate(raw)
        if path.status != PathStatus.CANDIDATE:
            continue  # disproved paths have no tool hops to replay
        path_events = replay_path(path, fixtures, policy=policy, approvals=queue)
        path_event_map[path.path_id] = [e.event_id for e in path_events]
        events.extend(path_events)
    report = ReplayReport(
        replay_events=[e.model_dump(mode="json") for e in events],
        path_event_map=path_event_map,
    )
    return {"replay": report.model_dump(mode="json")}


def policy_verifier_node(state: dict) -> dict:
    """Policy Verifier: assign final statuses from the replay verdicts.

    Wraps the pure evaluator results recorded per hop — no model may override.
    """
    from app.orchestrator.messages import VerifyRequest

    path_find = PathFindReport.model_validate(state["path_find"])
    replay = ReplayReport.model_validate(state["replay"])
    req = VerifyRequest(paths=path_find.paths, replay_events=replay.replay_events)

    events = [ReplayEvent.model_validate(raw) for raw in req.replay_events]
    parsed = [Path.model_validate(raw) for raw in req.paths]
    blocked_reasons: dict[str, list] = {}
    blocked_rules: dict[str, set] = {}
    event_map = replay.path_event_map if hasattr(replay, "path_event_map") else {}
    for path in parsed:
        if path.status != PathStatus.CANDIDATE:
            continue
        my_event_ids = set(event_map.get(path.path_id, []))
        for event in events:
            if event.decision == "blocked" and event.event_id in my_event_ids:
                blocked_reasons.setdefault(path.path_id, []).extend(event.policy.reasons)
                blocked_rules.setdefault(path.path_id, set()).update(event.policy.rule_ids)

    out_paths = []
    for path in parsed:
        if path.status == PathStatus.DISPROVED:
            path = path.model_copy(update={
                "basis": Basis.POLICY_VERIFIER,
                "history": path.history + [
                    PathHistoryEntry(status=PathStatus.DISPROVED, at_step="policy_verifier")],
            })
        elif path.path_id in blocked_reasons:
            reasons = blocked_reasons[path.path_id]
            path = path.model_copy(update={
                "status": PathStatus.BLOCKED,
                "basis": Basis.POLICY_VERIFIER,
                "rule_refs": sorted(blocked_rules[path.path_id], key=lambda r: r.value),
                "reasons": [r.model_dump(mode="json") for r in reasons],
                "history": path.history + [
                    PathHistoryEntry(status=PathStatus.BLOCKED, at_step="policy_verifier")],
            })
        else:
            path = path.model_copy(update={
                "status": PathStatus.ALLOWED,
                "basis": Basis.POLICY_VERIFIER,
                "history": path.history + [
                    PathHistoryEntry(status=PathStatus.ALLOWED, at_step="policy_verifier")],
            })
        out_paths.append(path.model_dump(by_alias=True, mode="json"))
    report = VerifyReport(paths=out_paths)
    return {"verify": report.model_dump(mode="json")}


def _collect_findings(paths: list[dict]) -> list[dict]:
    """Verifier findings from blocked paths, as typed {code, rule_id, path_id}."""
    out = []
    for p in paths:
        if p["status"] == "blocked":
            for reason in p["reasons"]:
                out.append({"code": reason["code"], "rule_id": reason["rule_id"],
                            "path_id": p["path_id"]})
    return out


def evidence_writer_node(state: dict) -> dict:
    """Evidence Writer: assemble the RunResponse + hash-chained evidence."""
    from app.contracts import Edge as _E  # noqa: F401
    from app.contracts import Graph
    from app.orchestrator.messages import EvidenceRequest

    verify = VerifyReport.model_validate(state["verify"])
    replay = ReplayReport.model_validate(state["replay"])
    inventory = InventoryReport.model_validate(state["inventory"])
    scenario = ScenarioResponse.model_validate(inventory.scenario)
    graph = Graph.model_validate(state["graph"])
    policy = load_policy()

    run_id = uuid.uuid4().hex[:26].upper()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    paths = verify.paths
    counts = SummaryCounts(
        nodes=len(graph.nodes), edges=len(graph.edges),
        candidate_paths=sum(1 for p in paths if p["status"] == "candidate"),
        allowed_paths=sum(1 for p in paths if p["status"] == "allowed"),
        blocked_paths=sum(1 for p in paths if p["status"] == "blocked"),
        disproved_paths=sum(1 for p in paths if p["status"] == "disproved"),
    )
    summary = Summary(
        headline="Compositional path from untrusted document to finance.export found and blocked",
        counts=counts, sensitive_sinks=scenario.sensitive_sinks,
        tools_tested=len(scenario.manifest.tools), identities=len(scenario.identities),
        rules=len(scenario.policy.rules),
    )

    # Evidence: fixture sources + replay events + orchestration trace, hash-chained.
    records: list[dict] = []
    prev_hash = None

    def add_record(evidence_id, kind, source_id, summary_text, trace):
        nonlocal prev_hash
        rec = {
            "evidence_id": evidence_id, "kind": kind, "run_id": run_id,
            "captured_at": generated_at, "source_id": source_id,
            "summary": summary_text, "prev_hash": prev_hash,
            "trace": trace,
        }
        rec["hash"] = compute_hash(prev_hash, rec)
        prev_hash = rec["hash"]
        records.append(rec)

    add_record("src:doc-untrusted-001", "source", "src:doc-untrusted-001",
               "seeded untrusted vendor note containing an injection fixture",
               {"path_ids": [p["path_id"] for p in paths], "event_ids": []})
    add_record("src:manifest", "manifest", "src:manifest",
               "tool manifest loaded", {"path_ids": [], "event_ids": []})
    add_record("src:grant-matrix", "grant", "src:grant-matrix",
               "identity/tool grant matrix loaded", {"path_ids": [], "event_ids": []})
    for rule in policy.rules:
        add_record(f"src:policy-rule-{rule['id'][-1].lower()}", "policy_rule",
                   f"src:policy-rule-{rule['id'][-1].lower()}",
                   f"{rule['id']} {rule['name']}", {"path_ids": [], "event_ids": []})
    # Orchestrator trace: contract EvidenceKind is closed, so these are kind "event".
    for i, role in enumerate(ROLE_NAMES, start=1):
        add_record(f"evt:orch-{i:02d}", "event", "src:manifest",
                   f"orchestrator role={role} (timings stripped)",
                   {"path_ids": [], "event_ids": []})
    for raw in replay.replay_events:
        event = ReplayEvent.model_validate(raw)
        add_record(event.event_id, "event",
                   event.source_ids[0],
                   f"replay {event.tool} -> {event.decision}",
                   {"path_ids": [], "event_ids": [event.event_id]})

    req = EvidenceRequest(
        run_id=run_id, scenario_id=scenario.scenario_id, graph=state["graph"],
        paths=paths, replay_events=replay.replay_events,
        input_digest=inventory.input_digest,
    )

    # BE-10: real recommendation, in-memory diff, and retests from findings.
    from app.policy.diff import build_policy_diff
    from app.policy.recommend import build_recommendation
    from app.retest import run_retests

    fixtures = load_fixtures()
    findings = _collect_findings(paths)
    recommendation = build_recommendation(findings)
    policy_diff = build_policy_diff(policy, recommendation["changes"], fixtures.grants)
    paths_by_id = {p["path_id"]: Path.model_validate(p) for p in paths}
    # RT-3 assumes a real queue approval exists for the finance workflow.
    queue_approval = [ApprovalRef(approval_id="ap-queue", status=ApprovalStatus.APPROVED,
                                  origin=AuthBasis.HUMAN_APPROVAL)]
    retests = run_retests(paths_by_id, fixtures, policy, recommendation["changes"],
                          approvals=queue_approval)
    approval = ApprovalState(
        status=ApprovalStatus.PENDING,
        items=[{
            "approval_id": "ap-1",
            "subject": {"type": "recommendation", "id": "REC-1"},
            "status": "pending",
            "requested_at": generated_at,
            "decided_by": None, "decided_at": None, "note": None,
            "applied": False, "simulated": True,
            "effect": "records a decision only; no policy or tool action is performed",
        }],
    )
    run = RunResponse(
        schema_version="1.0.0", run_id=req.run_id, scenario_id=req.scenario_id,
        status=RunStatus.COMPLETED, deterministic=True, generated_at=generated_at,
        input_digest=req.input_digest,
        engine={"policy_engine": policy.engine, "orchestrator": "langgraph@1.2.20"},
        summary=summary,
        graph=graph,
        paths=[Path.model_validate(p) for p in req.paths],
        replay_events=[ReplayEvent.model_validate(e) for e in req.replay_events],
        policy_diff=policy_diff,
        recommendation=recommendation,
        retests=retests,
        approval=approval,
        evidence=[EvidenceRecord.model_validate(r) for r in records],
    )
    report = EvidenceReport(run=run.model_dump(by_alias=True, mode="json"))
    return {"evidence": report.model_dump(mode="json")}
