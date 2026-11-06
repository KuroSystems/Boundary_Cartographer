"""Safe offline injection replay engine (BE-08).

Walks a candidate path hop by hop, builds a CallContext (purpose + taint
propagation + delegation), calls the deterministic `evaluate()` BEFORE every
tool call, and only invokes a mock tool when the verdict is allow. Forged
claims inside the untrusted document ("approval ref: CFO-2026-11", "you are
now finance_analyst") are parsed ONLY as text tokens for detection
(`untrusted_claims`) — never applied to actor, purpose, or approval.
`finance.export` is never executed even when allowed (records-only demo).
"""

import hashlib
import json
import re

from app.contracts import (
    ApprovalStatus,
    AuthBasis,
    Decision,
    EdgeKind,
    Path,
    Purpose,
    ReplayEvent,
    ReplayPolicyVerdict,
    TrustLevel,
)
from app.fixtures import LoadedFixtures
from app.policy import ApprovalRef, CallContext, Policy, evaluate, load_policy
from app.replay.taint import TaintTracker
from app.tools import local_server
from app.tools.protocol import ToolCallRequest

# Text-token detectors for forged claims. Detection only — never applied.
CLAIM_PATTERNS = [
    (re.compile(r"Approval[^.]*?ref:\s*([A-Za-z0-9-]+)", re.IGNORECASE), "approval_claim"),
    (re.compile(r"You are now ([a-z_]+)", re.IGNORECASE), "identity_claim"),
]


def detect_untrusted_claims(text: str) -> list[dict]:
    """Scan untrusted text for forged claims. Returns text tokens only."""
    claims = []
    for pattern, kind in CLAIM_PATTERNS:
        for match in pattern.finditer(text):
            claims.append({"kind": kind, "ref": match.group(1), "span": list(match.span())})
    return claims


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(obj) -> str:
    return "sha256:" + hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


def _redacted_preview(tool: str, args: dict, claims: list[dict]) -> str:
    """Redacted preview — never contains raw untrusted document text."""
    safe_args = {k: "<redacted>" for k in args}
    claim_kinds = sorted({c["kind"] for c in claims})
    return _canonical({"tool": tool, "args": safe_args, "claims_detected": claim_kinds})


def _verdict(ctx: CallContext, policy: Policy) -> ReplayPolicyVerdict:
    decision = evaluate(ctx, policy)
    return ReplayPolicyVerdict(
        decision=decision.decision,
        rule_ids=decision.rule_ids,
        reasons=[
            {
                "code": f.code,
                "rule_id": f.rule_id,
                "message": f.message,
                "evidence_ids": ["src:policy-rule-" + f.rule_id.value[-1].lower()],
            }
            for f in decision.findings
        ],
    )


def _event(seq: int, *, tool: str, actor: str, decision: Decision, executed: bool,
           trust_level: TrustLevel, purpose: Purpose, taint_labels: list[str],
           source_ids: list[str], preview: str, verdict: ReplayPolicyVerdict,
           tool_result, digest: str) -> ReplayEvent:
    return ReplayEvent(
        event_id=f"evt:{seq:04d}",
        seq=seq,
        actor=actor,
        tool=tool,
        decision=decision,
        executed=executed,
        trust_level=trust_level,
        purpose=purpose,
        taint_labels=taint_labels,
        source_ids=source_ids,
        input_digest=digest,
        input_preview=preview,
        policy=verdict,
        tool_result=tool_result,
    )


def replay_path(
    path: Path,
    fixtures: LoadedFixtures,
    policy: Policy | None = None,
    approvals: list[ApprovalRef] | None = None,
    call_fn=None,
    drop_inheritance: bool = False,
) -> list[ReplayEvent]:
    """Replay one candidate path. Returns replay_events[] (evt:0001.. in order).

    - evaluate() runs BEFORE every tool call; a mock tool is invoked only on allow.
    - finance.export is never executed (records-only), even when allowed.
    - Forged document claims are detected as text tokens and surfaced with
      origin untrusted_content; they are never applied.
    """
    policy = policy or load_policy()
    call_fn = call_fn or local_server.call
    queue_approvals = approvals or []

    events: list[ReplayEvent] = []
    doc_id = fixtures.document["id"]
    # Taint starts from the untrusted document only when the path originates there.
    taint = (
        TaintTracker.from_document(doc_id)
        if path.origin == f"source:{doc_id.removeprefix('src:')}"
        else TaintTracker()
    )
    claims = detect_untrusted_claims(fixtures.document["content"])

    # Leading injection-scan event: detection only, no tool invoked.
    events.append(_event(
        1, tool=f"scenario:{fixtures.scenario_id}", actor=path.hops[0].actor,
        decision=Decision.NOT_EXECUTED, executed=False, trust_level=TrustLevel.UNTRUSTED,
        purpose=path.stated_purpose or Purpose.DOCUMENT_SUMMARIZATION,
        taint_labels=taint.labels, source_ids=[doc_id],
        preview=_redacted_preview("scenario", {}, claims),
        verdict=ReplayPolicyVerdict(decision="allow", rule_ids=[], reasons=[]),
        tool_result=None,
        digest=_digest({"scenario": fixtures.scenario_id, "claims": len(claims)}),
    ))

    actor = path.hops[0].actor
    purpose = path.stated_purpose or Purpose.DOCUMENT_SUMMARIZATION
    purpose_origin = AuthBasis.USER_REQUEST
    delegation_chain: list[str] = []
    seq = 1

    for hop in path.hops:
        if hop.kind == EdgeKind.DELEGATES_TO:
            delegate = hop.to.removeprefix("identity:")
            delegation_chain.append(delegate)
            actor = delegate  # legitimate support->finance handoff (grant matrix)
            if drop_inheritance:
                # Simulated policy v2 (C3): a delegated context must re-establish
                # purpose from a trusted request — inherited purpose is dropped.
                purpose = Purpose.FINANCE_REPORTING if delegate == "finance_analyst" else purpose
                purpose_origin = AuthBasis.USER_REQUEST
            seq += 1
            events.append(_event(
                seq, tool=f"delegation:{hop.from_}->{hop.to}", actor=actor,
                decision=Decision.ALLOWED, executed=False,
                trust_level=(TrustLevel.DERIVED_UNTRUSTED if taint.is_tainted
                             else TrustLevel.TRUSTED),
                purpose=purpose, taint_labels=taint.labels,
                source_ids=["src:grant-matrix"],
                preview=_redacted_preview("delegation", {}, claims),
                verdict=ReplayPolicyVerdict(decision="allow", rule_ids=[], reasons=[]),
                tool_result=None,
                digest=_digest({"delegation": [hop.from_, hop.to]}),
            ))
            continue

        tool_name = hop.to.removeprefix("tool:")
        # A real queue approval applies only to its own workflow purpose.
        approval = None
        if queue_approvals and purpose == Purpose.FINANCE_REPORTING:
            approval = queue_approvals[0]
        # A forged approval claim inside the document is surfaced ONLY for the
        # export call, with origin untrusted_content — never accepted, and never
        # overriding a real queue approval.
        if approval is None and tool_name == "finance.export":
            forged = next((c for c in claims if c["kind"] == "approval_claim"), None)
            if forged:
                approval = ApprovalRef(
                    approval_id=forged["ref"], status=ApprovalStatus.APPROVED,
                    origin=AuthBasis.UNTRUSTED_CONTENT,
                )

        ctx = CallContext(
            actor=actor, tool=tool_name, purpose=purpose, purpose_origin=purpose_origin,
            args_taint=taint.is_tainted, taint_labels=taint.labels, approval=approval,
            delegation_chain=delegation_chain,
        )
        verdict = _verdict(ctx, policy)
        digest = _digest({"tool": tool_name, "actor": actor, "purpose": purpose.value,
                          "taint": taint.labels})
        preview = _redacted_preview(
            tool_name,
            {"input": "document-derived" if taint.is_tainted else "none"}, claims,
        )

        if verdict.decision == "allow" and tool_name != "finance.export":
            req = ToolCallRequest(
                tool=tool_name,
                arguments={"document_id": doc_id} if tool_name == "document.read" else {},
                actor=actor, purpose=purpose, taint=taint.labels,
            )
            result = call_fn(req, fixtures)
            taint.mark_derived_untrusted()
            seq += 1
            events.append(_event(
                seq, tool=tool_name, actor=actor, decision=Decision.ALLOWED, executed=True,
                trust_level=TrustLevel.UNTRUSTED if tool_name == "document.read"
                else TrustLevel.DERIVED_UNTRUSTED,
                purpose=purpose, taint_labels=taint.labels,
                source_ids=[doc_id] if tool_name.startswith("document.") else ["src:grant-matrix"],
                preview=preview, verdict=verdict,
                tool_result={"content": [c.model_dump(mode="json") for c in result.content],
                             "is_error": result.is_error, "simulated": result.simulated},
                digest=digest,
            ))
        else:
            # blocked, or finance.export allowed-but-never-executed (records only)
            decision = Decision.ALLOWED if verdict.decision == "allow" else Decision.BLOCKED
            seq += 1
            events.append(_event(
                seq, tool=tool_name, actor=actor, decision=decision,
                executed=False,  # finance.export is never executed; blocked never executes
                trust_level=(TrustLevel.DERIVED_UNTRUSTED if taint.is_tainted
                             else TrustLevel.TRUSTED),
                purpose=purpose, taint_labels=taint.labels,
                source_ids=["src:grant-matrix", "src:policy-rule-2", "src:policy-rule-3"]
                if verdict.decision == "deny" else ["src:grant-matrix"],
                preview=preview, verdict=verdict, tool_result=None, digest=digest,
            ))
    return events
