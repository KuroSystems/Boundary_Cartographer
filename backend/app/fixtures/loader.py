"""Fixtures loader (BE-02): loads manifest, identities, grant matrix, policy, seeded
document; cross-validates them; computes input_digest = sha256 of canonical JSON of
manifest+identities+grants+policy+doc; assembles the ScenarioResponse for
GET /api/v1/scenarios/demo.

Fully offline: reads only files under backend/app/fixtures/.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from app.contracts import Purpose, ScenarioResponse

FIXTURES_DIR = Path(__file__).resolve().parent


class FixtureError(Exception):
    """Base class for fixture loading/cross-validation errors."""


class UnknownToolInGrant(FixtureError):
    """A grant references a tool that is not in the manifest."""


class UnknownIdentityInGrant(FixtureError):
    """A grant references an identity that does not exist."""


class UnknownPurpose(FixtureError):
    """A purpose string is not one of the closed contract purposes."""


class DuplicateRuleId(FixtureError):
    """A policy rule id appears more than once."""


class MissingSeededDocument(FixtureError):
    """The seeded untrusted document file is missing."""


@dataclass
class LoadedFixtures:
    scenario_id: str
    name: str
    manifest: dict
    identities: list[dict]
    grants: list[dict]
    policy: dict
    document: dict
    sensitive_sinks: list[str]
    input_digest: str

    def scenario_response(self) -> ScenarioResponse:
        """Assemble (and validate via Pydantic) the ScenarioResponse payload."""
        # Project policy rules into the contract shape (PolicyRuleMeta has no
        # kind/conditions — those stay engine-side data in the YAML).
        policy_meta = {
            "policy_id": self.policy["policy_id"],
            "engine": self.policy["engine"],
            "rules": [
                {
                    "id": rule["id"],
                    "name": rule["name"],
                    "effect": rule["effect"],
                    "reason_codes": rule["reason_codes"],
                    "summary": rule["summary"],
                }
                for rule in self.policy["rules"]
            ],
        }
        return ScenarioResponse.model_validate({
            "schema_version": "1.0.0",
            "scenario_id": self.scenario_id,
            "name": self.name,
            "manifest": {"tools": self.manifest["tools"]},
            "identities": self.identities,
            "grants": self.grants,
            "policy": policy_meta,
            "document": self.document,
            "sensitive_sinks": self.sensitive_sinks,
        })


def _canonical_digest(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_yaml(base_dir: Path, relative: str) -> dict:
    path = base_dir / relative
    if not path.is_file():
        raise FixtureError(f"missing fixture file: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise FixtureError(f"fixture file {path} must contain a YAML mapping")
    return data


def _validate_purposes(purposes: list[str], where: str) -> None:
    valid = {p.value for p in Purpose}
    for purpose in purposes:
        if purpose not in valid:
            raise UnknownPurpose(f"unknown purpose {purpose!r} in {where}; valid: {sorted(valid)}")


def load_fixtures(base_dir: Path | None = None) -> LoadedFixtures:
    """Load and cross-validate all fixtures. Raises specific FixtureError subclasses."""
    base = Path(base_dir) if base_dir is not None else FIXTURES_DIR

    manifest = _load_yaml(base, "manifest.yaml")
    identities_doc = _load_yaml(base, "identities.yaml")
    grants_doc = _load_yaml(base, "grants.yaml")
    policy = _load_yaml(base, "policies/demo-policy-v1.yaml")

    tools = manifest.get("tools") or []
    identities = identities_doc.get("identities") or []
    grants = grants_doc.get("grants") or []
    rules = policy.get("rules") or []

    tool_names = {t["name"] for t in tools}
    identity_ids = {i["id"] for i in identities}

    # --- cross-validation with specific errors ---
    for grant in grants:
        if grant["tool"] not in tool_names:
            raise UnknownToolInGrant(
                f"grant references unknown tool {grant['tool']!r}; known: {sorted(tool_names)}"
            )
        if grant["identity"] not in identity_ids:
            raise UnknownIdentityInGrant(
                f"grant references non-existent identity {grant['identity']!r}; "
                f"known: {sorted(identity_ids)}"
            )
        _validate_purposes(grant.get("purposes", []), f"grant {grant['identity']}->{grant['tool']}")
    for identity in identities:
        _validate_purposes(identity.get("allowed_purposes", []), f"identity {identity['id']}")
        for delegate in identity.get("may_delegate_to", []):
            if delegate not in identity_ids:
                raise UnknownIdentityInGrant(
                    f"identity {identity['id']} delegates to unknown {delegate!r}"
                )
    for tool in tools:
        _validate_purposes(tool.get("purposes", []), f"tool {tool['name']}")

    seen_rule_ids: set[str] = set()
    for rule in rules:
        if rule["id"] in seen_rule_ids:
            raise DuplicateRuleId(f"duplicate policy rule id {rule['id']!r}")
        seen_rule_ids.add(rule["id"])

    # --- seeded document ---
    seeded = manifest.get("seeded_document") or {}
    doc_file = base / seeded.get("file", "")
    if not doc_file.is_file():
        raise MissingSeededDocument(f"seeded document missing: {doc_file}")
    content = doc_file.read_text(encoding="utf-8")
    document = {
        "id": seeded["id"],
        "title": seeded["title"],
        "trust_level": seeded["trust_level"],
        "content_is_data": bool(seeded.get("content_is_data", True)),
        "content": content,
        "source_ids": [seeded["id"]],
    }

    digest_payload = {
        "manifest": manifest,
        "identities": identities,
        "grants": grants,
        "policy": policy,
        "document": document,
    }

    return LoadedFixtures(
        scenario_id=manifest["scenario_id"],
        name=manifest["name"],
        manifest=manifest,
        identities=identities,
        grants=grants,
        policy=policy,
        document=document,
        sensitive_sinks=list(manifest.get("sensitive_sinks", [])),
        input_digest=_canonical_digest(digest_payload),
    )
