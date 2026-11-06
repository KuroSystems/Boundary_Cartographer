"""BE-04 acceptance tests: mock MCP tool boundary and the four tools."""

import ast
import builtins
import socket
from pathlib import Path

import pytest

from app.contracts import Purpose
from app.fixtures import FIXTURES_DIR, load_fixtures
from app.tools import TOOL_ORDER, ToolCallRequest, call, list_tools

TOOLS_PKG = Path(__file__).resolve().parents[1] / "app" / "tools"


@pytest.fixture()
def fixtures():
    return load_fixtures()


def _req(tool: str, **kwargs) -> ToolCallRequest:
    base = {
        "tool": tool,
        "arguments": {},
        "actor": "document_assistant",
        "purpose": Purpose.DOCUMENT_SUMMARIZATION,
        "taint": [],
    }
    base.update(kwargs)
    return ToolCallRequest(**base)


def test_list_tools_exactly_four_in_declared_order_simulated():
    tools = list_tools()
    assert [t["name"] for t in tools] == TOOL_ORDER == [
        "document.read", "document.summarize", "finance.lookup", "finance.export",
    ]
    assert all(t["simulated"] is True for t in tools)


def test_every_result_is_simulated(fixtures):
    for tool in TOOL_ORDER:
        result = call(_req(tool), fixtures)
        assert result.simulated is True
        assert result.is_error is False


def test_finance_export_simulated_and_writes_nothing(fixtures, monkeypatch):
    def _fail(*args, **kwargs):
        raise AssertionError("finance.export attempted file/socket I/O")

    monkeypatch.setattr(socket, "socket", _fail)
    monkeypatch.setattr(socket, "create_connection", _fail)
    monkeypatch.setattr(builtins, "open", _fail)

    result = call(_req("finance.export", arguments={"scope": "full_ledger"}), fixtures)
    data = result.content[0].data
    assert data == {
        "status": "SIMULATED",
        "exported": False,
        "records": 0,
        "note": "no real export performed",
    }


def test_unknown_tool_returns_error_not_raise(fixtures):
    result = call(_req("rm_rf.everything"), fixtures)
    assert result.is_error is True
    assert result.code == "UNKNOWN_TOOL"
    assert result.simulated is True
    assert result.content[0].data["code"] == "UNKNOWN_TOOL"


def test_document_read_returns_seeded_text_verbatim(fixtures):
    result = call(
        _req("document.read", arguments={"document_id": "src:doc-untrusted-001"}), fixtures
    )
    data = result.content[0].data
    raw = (FIXTURES_DIR / "documents" / "untrusted_vendor_note.md").read_text(encoding="utf-8")
    assert data["content"] == raw  # verbatim string, never interpreted
    assert data["content_is_data"] is True
    assert data["trust_level"] == "untrusted"
    assert result.source_ids == ["src:doc-untrusted-001"]


def test_document_summarize_deterministic_and_derived(fixtures):
    r1 = call(_req("document.summarize", arguments={"text": "abc"}), fixtures)
    r2 = call(_req("document.summarize", arguments={"text": "abc"}), fixtures)
    assert r1.content[0].data == r2.content[0].data
    assert r1.content[0].data["derived_from"] == ["src:doc-untrusted-001"]
    assert r1.content[0].data["chars"] == 3


def test_finance_lookup_two_fixed_rows(fixtures):
    result = call(_req("finance.lookup", arguments={"query": "invoices"}), fixtures)
    data = result.content[0].data
    assert data["count"] == 2
    assert data["rows"][0]["account"] == "acct-1001"


def test_no_eval_exec_in_tools_package():
    banned = {"eval", "exec", "compile", "__import__"}
    for path in sorted(TOOLS_PKG.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in banned, f"{path.name} calls {node.func.id}()"
            if isinstance(node, ast.Attribute) and node.attr in banned:
                assert False, f"{path.name} uses .{node.attr}"
