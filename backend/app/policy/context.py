"""Call context for the deterministic policy evaluator (BE-07).

Pure data. `purpose_origin` / `approval.origin` carry the authorization basis
(AuthBasis) — `untrusted_content` is never sufficient and always denied (R1).
"""

from pydantic import BaseModel, ConfigDict, Field

from app.contracts import ApprovalStatus, AuthBasis, Purpose


class ApprovalRef(BaseModel):
    """A referenced approval-queue entry and where the claim came from."""

    model_config = ConfigDict(extra="forbid")

    approval_id: str | None = None
    status: ApprovalStatus
    # human_approval for real queue entries; untrusted_content if the document claimed it
    origin: AuthBasis


class CallContext(BaseModel):
    """Everything the rule engine may look at for one tool call. No I/O fields."""

    model_config = ConfigDict(extra="forbid")

    actor: str
    tool: str
    purpose: Purpose
    purpose_origin: AuthBasis
    args_taint: bool
    taint_labels: list[str] = Field(default_factory=list)
    approval: ApprovalRef | None = None
    delegation_chain: list[str] = Field(default_factory=list)
