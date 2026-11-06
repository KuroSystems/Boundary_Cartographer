"""Deterministic policy evaluator (BE-07, ADR-0001).

`evaluate(ctx, policy) -> PolicyDecision` — a pure function: no I/O, no LLM,
no randomness, no wall-clock reads. Default deny: any finding denies; all
matched denials are returned ordered by precedence R1 > R3 > R2, and the first
is the primary reason. Same input ⇒ byte-identical decision.
"""

from pydantic import BaseModel, ConfigDict

from app.contracts import PolicyDecision as PolicyDecisionEnum
from app.contracts import RuleId
from app.policy.context import CallContext
from app.policy.engine import Policy, load_policy
from app.policy.rules import RULES, RuleFinding

# Denial precedence (tasks.md §2.3): first match is the primary reason.
PRECEDENCE = [RuleId.R1, RuleId.R3, RuleId.R2]


class PolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: PolicyDecisionEnum
    primary_reason: RuleFinding | None = None
    findings: list[RuleFinding]
    rule_ids: list[RuleId]


def evaluate(ctx: CallContext, policy: Policy | None = None) -> PolicyDecision:
    """Pure evaluation of all rules against the call context. Default deny."""
    policy = policy or load_policy()
    findings: list[RuleFinding] = []
    for rule_id in PRECEDENCE:  # R1 > R3 > R2
        if rule_id.value not in {r["id"] for r in policy.rules}:
            continue
        findings.extend(RULES[rule_id](ctx))
    if findings:
        return PolicyDecision(
            decision=PolicyDecisionEnum.DENY,
            primary_reason=findings[0],
            findings=findings,
            rule_ids=[f.rule_id for f in findings],
        )
    return PolicyDecision(
        decision=PolicyDecisionEnum.ALLOW,
        primary_reason=None,
        findings=[],
        rule_ids=[],
    )
