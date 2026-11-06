"""Safety and offline guarantees (BE-13).

Global guards live in conftest.py and are active for the whole suite:
- `socket.socket` / `socket.create_connection` raise (no network);
- `open()` in any write mode raises outside tmp_path (fixtures are read-only).

This module contains the self-tests proving the guards trip, the
"export never executed" invariant, the AST/import scan for dangerous
constructs and HTTP clients, the fixture-hash stability check, and the
untrusted-content-as-instructions regression.
"""

import ast
import hashlib
import socket
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_APP = REPO_ROOT / "backend" / "app"
FIXTURES_DIR = BACKEND_APP / "fixtures"

# Modules that must never appear as imports in app/policy, app/orchestrator,
# app/tools (authorization must never depend on an LLM or an HTTP client).
BLOCKED_IMPORTS = {
    "httpx", "requests", "urllib", "urllib3", "aiohttp", "openai", "anthropic",
    "subprocess", "ftplib", "smtplib", "telnetlib",
}
DANGEROUS_CALLS = {"eval", "exec", "os.system", "subprocess", "compile"}


def _py_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def _tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(root.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts:
            h.update(str(f.relative_to(root)).encode())
            h.update(f.read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------- guards
def test_network_guard_trips():
    with pytest.raises(AssertionError, match="offline"):
        socket.create_connection(("example.com", 443))
    with pytest.raises(AssertionError, match="offline"):
        socket.getaddrinfo("example.com", 443)
    s = socket.socket()
    try:
        with pytest.raises(AssertionError, match="offline"):
            s.connect(("127.0.0.1", 80))
    finally:
        s.close()


def test_write_guard_trips_outside_tmp(tmp_path):
    probe = FIXTURES_DIR / "__guard_probe__.tmp"
    try:
        with pytest.raises(AssertionError, match="outside tmp_path"):
            open(probe, "w")
        assert not probe.exists()
    finally:
        if probe.exists():
            probe.unlink()
    # sanity: writes under tmp_path are still allowed
    ok = tmp_path / "allowed.txt"
    ok.write_text("fine")
    assert ok.read_text() == "fine"


# ------------------------------------------------- dangerous constructs
@pytest.mark.parametrize("pkg", ["policy", "orchestrator", "tools"])
def test_core_packages_import_no_http_client_or_subprocess(pkg):
    root = BACKEND_APP / pkg
    offenders = []
    for f in _py_files(root):
        tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module.split(".")[0]]
            for m in mods:
                if m in BLOCKED_IMPORTS:
                    offenders.append(f"{f.relative_to(REPO_ROOT)}: imports {m}")
    assert not offenders, "blocked imports in core packages:\n" + "\n".join(offenders)


def test_no_eval_exec_subprocess_anywhere_in_backend():
    offenders = []
    for f in _py_files(BACKEND_APP):
        tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = ""
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = f"{ast.unparse(func.value)}.{func.attr}"
                if name in DANGEROUS_CALLS or name.split(".")[-1] in {"eval", "exec", "system"}:
                    offenders.append(f"{f.relative_to(REPO_ROOT)}:{node.lineno}: call {name}()")
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.split(".")[0] in BLOCKED_IMPORTS:
                        rel = f.relative_to(REPO_ROOT)
                        offenders.append(f"{rel}:{node.lineno}: import {a.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in BLOCKED_IMPORTS:
                    rel = f.relative_to(REPO_ROOT)
                    offenders.append(f"{rel}:{node.lineno}: from {node.module}")
    assert not offenders, "dangerous constructs found:\n" + "\n".join(offenders)


# ------------------------------------------------------- invariants
def test_finance_export_never_executed_property(run_factory):
    """Property over the run response: no reachable path executes finance.export."""
    for _ in range(2):  # two independent runs
        resp, _run_id = run_factory()
        assert resp.status_code == 201
        run = resp.json()
        export_events = [e for e in run["replay_events"]
                         if e["tool"] == "finance.export"]
        assert export_events, "expected at least one finance.export replay event"
        for e in export_events:
            # the sensitive sink is simulated-only: never actually executed
            assert e["executed"] is False, f"finance.export executed in {e['event_id']}"
        # attack paths (document -> export) are blocked; only the legitimate
        # finance workflow (P5) reaches the export, and still unexecuted
        attack = [p for p in run["paths"]
                  if p["status"] != "disproved" and p["path_id"] != "P5"
                  and any("finance.export" in h.get("tool", "") for h in p.get("hops", []))]
        assert all(p["status"] == "blocked" for p in attack)


def test_fixtures_unchanged_by_analysis_and_approval(client, run_factory):
    before = _tree_digest(FIXTURES_DIR)
    resp, run_id = run_factory()
    client.post(f"/api/v1/runs/{run_id}/approval",
                json={"approval_id": "ap-1", "decision": "approve",
                      "decided_by": "safety-test"})
    client.get("/api/v1/scenarios/demo")
    assert _tree_digest(FIXTURES_DIR) == before, "app/fixtures/** changed during the suite"


def test_untrusted_content_never_authorizes_regression(run_factory):
    """The seeded document carries a forged approval claim; it must never
    turn into authorization (R1) nor a valid queue approval (R3)."""
    resp, _ = run_factory()
    run = resp.json()
    doc = run  # paths carry the verdicts
    blocked = {p["path_id"]: p for p in doc["paths"] if p["status"] == "blocked"}
    assert set(blocked) == {"P1", "P2"}
    export_events = [e for e in run["replay_events"]
                     if e["tool"] == "finance.export" and e["decision"] == "blocked"]
    assert export_events
    for e in export_events:
        codes = {r["code"] for r in e["policy"]["reasons"]}
        assert codes & {"R1_INSTRUCTION_NOT_AUTHORIZATION", "R3_NO_VALID_APPROVAL"}, (
            f"forged claim in untrusted document was not rejected: {codes}"
        )
    # no path may cite untrusted_content as its basis
    for p in run["paths"]:
        assert p["basis"] != "untrusted_content"
