"""Pydantic v2 domain models for the frozen v1 contract (BE-01).

Every model uses `extra="forbid"` so unknown fields are rejected, matching
`additionalProperties: false` in `contract/schemas/*.json`. `model_json_schema()`
for `RunResponse` / `ScenarioResponse` is diffed against those contract schemas in
`backend/tests/test_contract_models.py` (required fields + enums; drift fails).
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import (
    ApprovalStatus,
    Basis,
    ChangeOp,
    Decision,
    EdgeKind,
    EvidenceKind,
    NodeKind,
    NodeRisk,
    PathStatus,
    PolicyDecision,
    Purpose,
    RetestId,
    RuleId,
    RunStatus,
    TrustLevel,
)

SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"
SEMVER_PATTERN = r"^\d+\.\d+\.\d+$"


class ContractModel(BaseModel):
    """Base: reject unknown fields (contract: additionalProperties: false)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# ---------------------------------------------------------------- graph
class Node(ContractModel):
    id: str
    kind: NodeKind
    label: str
    risk: NodeRisk | None = None
    scopes: list[str] = Field(default_factory=list)
    source_ids: list[str]


class Edge(ContractModel):
    id: str
    from_: str = Field(validation_alias="from", serialization_alias="from")
    to: str
    kind: EdgeKind
    purposes: list[Purpose] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)
    trust: TrustLevel | None = None
    source_ids: list[str]


class Graph(ContractModel):
    nodes: list[Node]
    edges: list[Edge]


# ---------------------------------------------------------------- paths
class PathHop(ContractModel):
    step: int = Field(ge=1)
    from_: str = Field(validation_alias="from", serialization_alias="from")
    to: str
    kind: EdgeKind
    actor: str
    purpose: Purpose


class PathReason(ContractModel):
    code: str
    rule_id: RuleId
    message: str
    evidence_ids: list[str]


class PathHistoryEntry(ContractModel):
    status: PathStatus
    at_step: str


class Path(ContractModel):
    path_id: str
    status: PathStatus
    basis: Basis
    origin: str
    sink: str
    stated_purpose: Purpose | None = None
    tainted: bool | None = None
    hops: list[PathHop]
    rule_refs: list[RuleId]
    reasons: list[PathReason]
    history: list[PathHistoryEntry]

    @model_validator(mode="after")
    def _enforce_status_invariants(self) -> "Path":
        # Contract invariants 1 & 2 (CONTRACT.md §4).
        if self.status == PathStatus.CANDIDATE:
            if self.basis != Basis.GRAPH_REACHABILITY:
                raise ValueError("candidate path must have basis == graph_reachability")
            if self.reasons:
                raise ValueError("candidate path must have no reasons[]")
        if self.status == PathStatus.BLOCKED and not self.reasons:
            raise ValueError("blocked path must have non-empty reasons[]")
        return self


# ---------------------------------------------------------------- replay
class ReplayPolicyVerdict(ContractModel):
    decision: PolicyDecision
    rule_ids: list[RuleId]
    reasons: list[PathReason]


class ReplayEvent(ContractModel):
    event_id: str
    seq: int = Field(ge=1)
    actor: str
    tool: str
    decision: Decision
    executed: bool
    trust_level: TrustLevel
    purpose: Purpose
    taint_labels: list[str]
    source_ids: list[str]
    input_digest: str = Field(pattern=SHA256_PATTERN)
    input_preview: str
    policy: ReplayPolicyVerdict
    tool_result: dict[str, Any] | list[Any] | str | int | float | bool | None

    @model_validator(mode="after")
    def _enforce_executed_invariant(self) -> "ReplayEvent":
        # Contract invariant 3 (CONTRACT.md §4): executed == false unless allowed.
        if self.decision != Decision.ALLOWED and self.executed:
            raise ValueError("executed must be false for any decision != allowed")
        return self


# ---------------------------------------------------------------- policy diff / recommendation
class PolicyRuleRef(ContractModel):
    id: RuleId
    summary: str


class GrantRef(ContractModel):
    identity: str
    tool: str
    scopes: list[str]


class PolicySnapshot(ContractModel):
    policy_id: str
    rules: list[PolicyRuleRef]
    grants: list[GrantRef]


class PolicyDiffChange(ContractModel):
    op: ChangeOp
    target: str
    rule_id: RuleId
    summary: str


class PolicyDiff(ContractModel):
    simulated: bool
    before: PolicySnapshot
    after: PolicySnapshot
    changes: list[PolicyDiffChange]

    @model_validator(mode="after")
    def _enforce_simulated(self) -> "PolicyDiff":
        # Contract invariant 7 (CONTRACT.md §4).
        if self.simulated is not True:
            raise ValueError("policy_diff.simulated must always be true")
        return self


class RecommendationChange(ContractModel):
    change_id: str
    op: ChangeOp
    target: str
    rule_refs: list[RuleId]


class Recommendation(ContractModel):
    recommendation_id: str
    title: str
    changes: list[RecommendationChange]
    expected_effect: dict[str, PathStatus]
    risk_if_unchanged: str
    generated_from: list[RuleId]


# ---------------------------------------------------------------- retests / approval
class Retest(ContractModel):
    retest_id: RetestId
    name: str
    expected: PathStatus
    actual: PathStatus
    passed: bool
    evidence_ids: list[str]


class ApprovalSubject(ContractModel):
    type: Literal["recommendation", "policy_change"]
    id: str


class ApprovalItem(ContractModel):
    approval_id: str
    subject: ApprovalSubject
    status: ApprovalStatus
    requested_at: datetime
    decided_by: str | None
    decided_at: datetime | None
    note: str | None
    applied: bool
    simulated: bool
    effect: str

    @model_validator(mode="after")
    def _enforce_records_only(self) -> "ApprovalItem":
        # Contract invariant 4 (CONTRACT.md §4): the queue records decisions only.
        if self.applied is not False:
            raise ValueError("approval item applied must always be false")
        if self.simulated is not True:
            raise ValueError("approval item simulated must always be true")
        return self


class ApprovalState(ContractModel):
    status: ApprovalStatus
    items: list[ApprovalItem]


# ---------------------------------------------------------------- evidence
class EvidenceTrace(ContractModel):
    path_ids: list[str]
    event_ids: list[str]


class EvidenceRecord(ContractModel):
    evidence_id: str
    kind: EvidenceKind
    run_id: str
    captured_at: datetime
    source_id: str
    summary: str
    hash: str = Field(pattern=SHA256_PATTERN)
    prev_hash: str | None
    trace: EvidenceTrace


# ---------------------------------------------------------------- run response
class EngineInfo(ContractModel):
    policy_engine: str
    orchestrator: str


class SummaryCounts(ContractModel):
    nodes: int = Field(ge=0)
    edges: int = Field(ge=0)
    candidate_paths: int = Field(ge=0)
    allowed_paths: int = Field(ge=0)
    blocked_paths: int = Field(ge=0)
    disproved_paths: int = Field(ge=0)


class Summary(ContractModel):
    headline: str
    counts: SummaryCounts
    sensitive_sinks: list[str]
    tools_tested: int
    identities: int
    rules: int


class RunResponse(ContractModel):
    schema_version: str = Field(pattern=SEMVER_PATTERN)
    run_id: str
    scenario_id: str
    status: RunStatus
    deterministic: bool
    generated_at: datetime
    input_digest: str = Field(pattern=SHA256_PATTERN)
    engine: EngineInfo
    summary: Summary
    graph: Graph
    paths: list[Path]
    replay_events: list[ReplayEvent]
    policy_diff: PolicyDiff
    recommendation: Recommendation
    retests: list[Retest]
    approval: ApprovalState
    evidence: list[EvidenceRecord]

    @model_validator(mode="after")
    def _enforce_run_invariants(self) -> "RunResponse":
        if self.deterministic is not True:
            raise ValueError("deterministic must always be true")
        if len(self.retests) != 3:
            raise ValueError("retests must always contain exactly RT-1, RT-2, RT-3")
        # Contract invariant 6 (CONTRACT.md §4): RT-2 present and allowed.
        rt2 = [r for r in self.retests if r.retest_id == RetestId.RT_2]
        if not rt2 or rt2[0].actual != PathStatus.ALLOWED:
            raise ValueError("retests must contain RT-2 with actual == allowed")
        # Contract invariant 3 (finance.export never executed).
        for event in self.replay_events:
            if event.tool == "finance.export" and event.executed:
                raise ValueError("finance.export must never have executed == true")
        return self


# ---------------------------------------------------------------- scenario response
class ToolManifestEntry(ContractModel):
    name: str
    description: str
    required_scopes: list[str]
    purposes: list[Purpose]
    sensitive: bool
    approval_required: bool


class Manifest(ContractModel):
    # Scope freeze (tasks.md §1.5): exactly four tools.
    tools: list[ToolManifestEntry] = Field(min_length=4, max_length=4)


class IdentityEntry(ContractModel):
    id: str
    label: str
    allowed_purposes: list[Purpose]
    may_delegate_to: list[str]


class GrantEntry(ContractModel):
    identity: str
    tool: str
    scopes: list[str]
    purposes: list[Purpose]
    note: str


class PolicyRuleMeta(ContractModel):
    id: RuleId
    name: str
    effect: Literal["deny"]
    reason_codes: list[str]
    summary: str


class PolicyMeta(ContractModel):
    policy_id: str
    engine: str
    # Scope freeze: exactly three rules R1, R2, R3.
    rules: list[PolicyRuleMeta] = Field(min_length=3, max_length=3)


class SeededDocument(ContractModel):
    id: str
    title: str
    trust_level: TrustLevel
    content_is_data: bool
    content: str
    source_ids: list[str]

    @model_validator(mode="after")
    def _enforce_content_is_data(self) -> "SeededDocument":
        # Untrusted document content is data, never instructions (tasks.md §1.5).
        if self.content_is_data is not True:
            raise ValueError("seeded document must have content_is_data == true")
        return self


class ScenarioResponse(ContractModel):
    schema_version: str = Field(pattern=SEMVER_PATTERN)
    scenario_id: str
    name: str
    manifest: Manifest
    # Scope freeze: exactly two identities.
    identities: list[IdentityEntry] = Field(min_length=2, max_length=2)
    grants: list[GrantEntry]
    policy: PolicyMeta
    document: SeededDocument
    sensitive_sinks: list[str]
