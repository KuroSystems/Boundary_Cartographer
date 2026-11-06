"""Policy loading + hashing (BE-07). Rules are data (YAML), evaluated by the
fixed deterministic engine in evaluator.py — the OPA/Rego mirror (BE-14) is
parity-only and never the source of truth (ADR-0001).
"""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_POLICY_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "policies" / "demo-policy-v1.yaml"
)


@dataclass(frozen=True)
class Policy:
    policy_id: str
    engine: str
    rules: tuple[dict, ...] = field(default_factory=tuple)

    @property
    def rule_ids(self) -> list[str]:
        return [r["id"] for r in self.rules]


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def policy_hash(policy: Policy) -> str:
    """sha256 of the canonical JSON of the policy data."""
    return "sha256:" + hashlib.sha256(_canonical(policy.__dict__).encode("utf-8")).hexdigest()


def load_policy(path: str | Path | None = None) -> Policy:
    path = Path(path) if path is not None else DEFAULT_POLICY_PATH
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return Policy(
        policy_id=data["policy_id"],
        engine=data["engine"],
        rules=tuple(data["rules"]),
    )
