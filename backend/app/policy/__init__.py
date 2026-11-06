"""Deterministic policy engine package (BE-07, ADR-0001)."""

from .context import ApprovalRef, CallContext
from .engine import Policy, load_policy, policy_hash
from .evaluator import PRECEDENCE, PolicyDecision, evaluate
from .rules import RULES, RuleFinding, rule_r1, rule_r2, rule_r3

__all__ = [
    "PRECEDENCE",
    "RULES",
    "ApprovalRef",
    "CallContext",
    "Policy",
    "PolicyDecision",
    "RuleFinding",
    "evaluate",
    "load_policy",
    "policy_hash",
    "rule_r1",
    "rule_r2",
    "rule_r3",
]
