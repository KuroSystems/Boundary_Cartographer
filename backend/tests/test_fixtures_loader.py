"""BE-02 acceptance tests for the fixtures loader."""

import shutil
from pathlib import Path

import pytest
import yaml

from app.contracts import ScenarioResponse
from app.fixtures import (
    FIXTURES_DIR,
    DuplicateRuleId,
    MissingSeededDocument,
    UnknownIdentityInGrant,
    UnknownPurpose,
    UnknownToolInGrant,
    load_fixtures,
)


@pytest.fixture()
def fixtures_copy(tmp_path: Path) -> Path:
    dest = tmp_path / "fixtures"
    shutil.copytree(FIXTURES_DIR, dest)
    return dest


def test_counts_and_sensitive_sink():
    loaded = load_fixtures()
    assert len(loaded.manifest["tools"]) == 4
    assert len(loaded.identities) == 2
    assert len(loaded.policy["rules"]) == 3
    assert loaded.document["id"] == "src:doc-untrusted-001"
    export = next(t for t in loaded.manifest["tools"] if t["name"] == "finance.export")
    assert export["sensitive"] is True
    assert loaded.sensitive_sinks == ["tool:finance.export"]
    # the marked over-grant is present
    over = next(
        g for g in loaded.grants
        if g["identity"] == "document_assistant" and g["tool"] == "finance.lookup"
    )
    assert "over-grant" in over["note"]


def test_input_digest_stable_across_two_loads():
    assert load_fixtures().input_digest == load_fixtures().input_digest
    assert load_fixtures().input_digest.startswith("sha256:")
    assert len(load_fixtures().input_digest) == len("sha256:") + 64


def test_input_digest_changes_when_any_fixture_byte_changes(fixtures_copy: Path):
    before = load_fixtures(fixtures_copy).input_digest
    doc = fixtures_copy / "documents" / "untrusted_vendor_note.md"
    doc.write_text(doc.read_text(encoding="utf-8") + "x", encoding="utf-8")
    after_doc = load_fixtures(fixtures_copy).input_digest
    assert after_doc != before

    grants = fixtures_copy / "grants.yaml"
    data = yaml.safe_load(grants.read_text(encoding="utf-8"))
    data["grants"][0]["note"] = "changed"
    grants.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert load_fixtures(fixtures_copy).input_digest != after_doc


def test_unknown_tool_in_grant_raises(fixtures_copy: Path):
    grants = fixtures_copy / "grants.yaml"
    data = yaml.safe_load(grants.read_text(encoding="utf-8"))
    data["grants"][0]["tool"] = "nonexistent.tool"
    grants.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(UnknownToolInGrant):
        load_fixtures(fixtures_copy)


def test_grant_for_nonexistent_identity_raises(fixtures_copy: Path):
    grants = fixtures_copy / "grants.yaml"
    data = yaml.safe_load(grants.read_text(encoding="utf-8"))
    data["grants"][0]["identity"] = "ghost_identity"
    grants.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(UnknownIdentityInGrant):
        load_fixtures(fixtures_copy)


def test_unknown_purpose_raises(fixtures_copy: Path):
    identities = fixtures_copy / "identities.yaml"
    data = yaml.safe_load(identities.read_text(encoding="utf-8"))
    data["identities"][0]["allowed_purposes"] = ["telepathy"]
    identities.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(UnknownPurpose):
        load_fixtures(fixtures_copy)


def test_duplicate_rule_id_raises(fixtures_copy: Path):
    policy = fixtures_copy / "policies" / "demo-policy-v1.yaml"
    data = yaml.safe_load(policy.read_text(encoding="utf-8"))
    data["rules"].append(dict(data["rules"][0]))
    policy.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(DuplicateRuleId):
        load_fixtures(fixtures_copy)


def test_missing_seeded_document_raises(fixtures_copy: Path):
    (fixtures_copy / "documents" / "untrusted_vendor_note.md").unlink()
    with pytest.raises(MissingSeededDocument):
        load_fixtures(fixtures_copy)


def test_scenario_response_assembled_from_loader_alone():
    loaded = load_fixtures()
    scenario = loaded.scenario_response()
    assert isinstance(scenario, ScenarioResponse)
    assert scenario.scenario_id == "demo-v1"
    assert len(scenario.manifest.tools) == 4
    assert len(scenario.identities) == 2
    assert [r.id for r in scenario.policy.rules] == ["R1", "R2", "R3"]
    assert scenario.document.content_is_data is True
    assert scenario.document.trust_level == "untrusted"
    assert "CFO-2026-11" in scenario.document.content  # injection fixture is data
    assert scenario.sensitive_sinks == ["tool:finance.export"]
    assert len(scenario.grants) == 5
