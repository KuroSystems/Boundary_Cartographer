"""In-process MCP-shaped tool server (BE-04, ADR-0002).

`list_tools()` / `call(req)` dispatch locally with fixed constants. No sockets,
no MCP SDK, no network. A real MCP client can later replace this module without
touching policy code — the typed boundary is the only seam.
"""

from app.fixtures import LoadedFixtures, load_fixtures
from app.tools.impl import TOOL_IMPLS
from app.tools.protocol import ToolCallRequest, ToolContentItem, ToolResult

# Declared order is part of the acceptance contract.
TOOL_ORDER = ["document.read", "document.summarize", "finance.lookup", "finance.export"]

_TOOL_DESCRIPTIONS = {
    "document.read": "Read the seeded untrusted document (mock, in-process).",
    "document.summarize": "Summarize document content (mock).",
    "finance.lookup": "Look up finance data (mock).",
    "finance.export": "Export a finance report (mock, simulated; sensitive sink).",
}

_default_fixtures: LoadedFixtures | None = None


def _fixtures(fixtures: LoadedFixtures | None) -> LoadedFixtures:
    global _default_fixtures
    if fixtures is not None:
        return fixtures
    if _default_fixtures is None:
        _default_fixtures = load_fixtures()
    return _default_fixtures


def list_tools() -> list[dict]:
    """`tools/list`: exactly the four tool names, in declared order, simulated."""
    return [
        {"name": name, "description": _TOOL_DESCRIPTIONS[name], "simulated": True}
        for name in TOOL_ORDER
    ]


def call(req: ToolCallRequest, fixtures: LoadedFixtures | None = None) -> ToolResult:
    """`tools/call`: in-process dispatch. Unknown tools return is_error, never raise."""
    impl = TOOL_IMPLS.get(req.tool)
    if impl is None:
        return ToolResult(
            tool=req.tool,
            content=[
                ToolContentItem(
                    type="json",
                    data={"code": "UNKNOWN_TOOL", "message": f"unknown tool {req.tool!r}"},
                )
            ],
            is_error=True,
            simulated=True,
            source_ids=["src:manifest"],
            code="UNKNOWN_TOOL",
        )
    return impl(req, _fixtures(fixtures))
