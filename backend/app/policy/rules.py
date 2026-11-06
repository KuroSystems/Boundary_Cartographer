"""Rules R1, R2, R3 as pure functions returning RuleFinding (BE-07).

Each rule inspects only the CallContext (+ policy data) and returns findings.
No I/O, no randomness, no clock, no LLM — same input ⇒ identical findings.
"""

from dataclasses import dataclass

from app.contracts import AuthBasis, Purpose, RuleId
from app.policy.context import CallContext

FINANCE_TOOLS = {"finance.lookup", "finance.export"}
EXPORT_TOOL = "finance.export"
EXPORT_ACTOR = "finance_analyst"
EXPORT_PURPOSE = Purpose.FINANCE_REPORTING


@dataclass(frozen=True)
class RuleFinding:
    rule_id: RuleId
    code: str
    message: str


def rule_r1(ctx: CallContext) -> list[RuleFinding]:
    """R1 — Untrusted content cannot authorize.

    Deny if any part of the authorization basis is untrusted_content:
    the purpose origin, or the approval claim's origin.
    """
    findings: list[RuleFinding] = []
    if ctx.purpose_origin == AuthBasis.UNTRUSTED_CONTENT:
        findings.append(RuleFinding(
            RuleId.R1, "R1_INSTRUCTION_NOT_AUTHORIZATION",
            "purpose was established from untrusted document content",
        ))
    if ctx.approval is not None and ctx.approval.origin == AuthBasis.UNTRUSTED_CONTENT:
        findings.append(RuleFinding(
            RuleId.R1, "R1_INSTRUCTION_NOT_AUTHORIZATION",
            f"approval claim originated from untrusted content (ref: {ctx.approval.approval_id})",
        ))
    return findings


def rule_r2(ctx: CallContext) -> list[RuleFinding]:
    """R2 — Purpose isolation.

    In a document_summarization workflow, deny finance.lookup / finance.export
    calls whose arguments contain document-derived (tainted) content.
    """
    if (
        ctx.purpose == Purpose.DOCUMENT_SUMMARIZATION
        and ctx.tool in FINANCE_TOOLS
        and ctx.args_taint
    ):
        return [RuleFinding(
            RuleId.R2, "R2_CROSS_PURPOSE_FLOW",
            f"{ctx.purpose.value} workflow sent document-derived content to {ctx.tool}",
        )]
    return []


def rule_r3(ctx: CallContext) -> list[RuleFinding]:
    """R3 — Export preconditions for finance.export.

    Allow only when actor == finance_analyst AND purpose == finance_reporting
    AND a valid human queue approval exists AND arguments are untainted.
    Each missing clause yields its own reason code.
    """
    if ctx.tool != EXPORT_TOOL:
        return []
    findings: list[RuleFinding] = []
    if ctx.actor != EXPORT_ACTOR:
        findings.append(RuleFinding(
            RuleId.R3, "R3_WRONG_IDENTITY",
            f"finance.export requires actor {EXPORT_ACTOR!r}, got {ctx.actor!r}",
        ))
    if ctx.purpose != EXPORT_PURPOSE:
        findings.append(RuleFinding(
            RuleId.R3, "R3_WRONG_PURPOSE",
            f"finance.export requires purpose {EXPORT_PURPOSE.value!r}, got {ctx.purpose.value!r}",
        ))
    if (
        ctx.approval is None
        or ctx.approval.status.value != "approved"
        or ctx.approval.origin != AuthBasis.HUMAN_APPROVAL
    ):
        findings.append(RuleFinding(
            RuleId.R3, "R3_NO_VALID_APPROVAL",
            "no valid human approval from the approval queue exists",
        ))
    if ctx.args_taint:
        findings.append(RuleFinding(
            RuleId.R3, "R3_TAINTED_ARGS",
            "finance.export arguments contain untrusted (tainted) content",
        ))
    return findings


RULES = {RuleId.R1: rule_r1, RuleId.R2: rule_r2, RuleId.R3: rule_r3}
