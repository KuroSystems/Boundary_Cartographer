"""Closed enums for the v1 contract (BE-01).

Values are identical strings to the closed enums in `contract/openapi.yaml` /
`contract/schemas/*.json` / `contract/CONTRACT.md` §5 — asserted by
`backend/tests/test_contract_models.py`.
"""

from enum import Enum


class StrEnum(str, Enum):
    """String enum that serializes to its value (keeps JSON output identical to the contract)."""

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.value


class RunStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class PathStatus(StrEnum):
    CANDIDATE = "candidate"
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    DISPROVED = "disproved"


class Basis(StrEnum):
    GRAPH_REACHABILITY = "graph_reachability"
    POLICY_VERIFIER = "policy_verifier"


class Decision(StrEnum):
    """Replay-event decision."""

    ALLOWED = "allowed"
    BLOCKED = "blocked"
    NOT_EXECUTED = "not_executed"


class PolicyDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


class TrustLevel(StrEnum):
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"
    DERIVED_UNTRUSTED = "derived_untrusted"
    MIXED = "mixed"


class NodeKind(StrEnum):
    SOURCE = "source"
    IDENTITY = "identity"
    TOOL = "tool"
    DATA_SCOPE = "data_scope"
    OUTPUT = "output"


class EdgeKind(StrEnum):
    FLOWS_TO = "flows_to"
    MAY_INVOKE = "may_invoke"
    READS = "reads"
    PRODUCES = "produces"
    DERIVED_FROM = "derived_from"
    DELEGATES_TO = "delegates_to"


class EvidenceKind(StrEnum):
    SOURCE = "source"
    MANIFEST = "manifest"
    GRANT = "grant"
    POLICY_RULE = "policy_rule"
    EVENT = "event"


class Purpose(StrEnum):
    DOCUMENT_SUMMARIZATION = "document_summarization"
    FINANCE_REPORTING = "finance_reporting"


class AuthBasis(StrEnum):
    """Authorization provenance. UNTRUSTED_CONTENT is never sufficient; always rejected (R1)."""

    USER_REQUEST = "user_request"
    POLICY_GRANT = "policy_grant"
    HUMAN_APPROVAL = "human_approval"
    SYSTEM_DEFAULT = "system_default"
    UNTRUSTED_CONTENT = "untrusted_content"


class RuleId(StrEnum):
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalDecisionValue(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class ChangeOp(StrEnum):
    REVOKE_GRANT = "revoke_grant"
    ADD_GUARD = "add_guard"
    DROP_INHERITANCE = "drop_inheritance"
    MODIFY = "modify"


class NodeRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RetestId(StrEnum):
    RT_1 = "RT-1"
    RT_2 = "RT-2"
    RT_3 = "RT-3"


class ErrorCode(StrEnum):
    SCENARIO_NOT_FOUND = "SCENARIO_NOT_FOUND"
    RUN_NOT_FOUND = "RUN_NOT_FOUND"
    APPROVAL_ALREADY_DECIDED = "APPROVAL_ALREADY_DECIDED"
    INVALID_DECISION = "INVALID_DECISION"
    VALIDATION_ERROR = "VALIDATION_ERROR"
