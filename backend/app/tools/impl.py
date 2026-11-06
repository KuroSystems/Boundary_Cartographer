"""The four mock tools (BE-04). Pure functions returning plain data only.

No eval/exec, no parsing of tool or document text into instructions, no I/O:
`document.read` returns the seeded text verbatim as a string; every other tool
returns fixed deterministic constants. `finance.export` never exports anything.
"""

from app.fixtures import LoadedFixtures
from app.tools.protocol import ToolCallRequest, ToolContentItem, ToolResult

SEEDED_DOC_ID = "src:doc-untrusted-001"

FINANCE_LOOKUP_ROWS = [
    {"account": "acct-1001", "currency": "USD", "balance": 12480.0},
    {"account": "acct-1002", "currency": "USD", "balance": 3210.5},
]

FINANCE_EXPORT_RESULT = {
    "status": "SIMULATED",
    "exported": False,
    "records": 0,
    "note": "no real export performed",
}


def _result(req: ToolCallRequest, data: dict, source_ids: list[str]) -> ToolResult:
    return ToolResult(
        tool=req.tool,
        content=[ToolContentItem(type="json", data=data)],
        is_error=False,
        simulated=True,
        source_ids=source_ids,
    )


def document_read(req: ToolCallRequest, fixtures: LoadedFixtures) -> ToolResult:
    """Return the seeded untrusted document verbatim as a string (data, not instructions)."""
    doc = fixtures.document
    return _result(
        req,
        {
            "document_id": doc["id"],
            "trust_level": doc["trust_level"],
            "content_is_data": True,
            "content": doc["content"],  # verbatim string; never interpreted
        },
        [SEEDED_DOC_ID],
    )


def document_summarize(req: ToolCallRequest, fixtures: LoadedFixtures) -> ToolResult:
    """Fixed deterministic mock summary; output is derived from the untrusted doc."""
    text = str(req.arguments.get("text", ""))
    return _result(
        req,
        {
            "summary": f"Mock summary of {len(text)} characters (simulated).",
            "chars": len(text),
            "derived_from": [SEEDED_DOC_ID],
        },
        [SEEDED_DOC_ID],
    )


def finance_lookup(req: ToolCallRequest, fixtures: LoadedFixtures) -> ToolResult:
    """Two fixed fake rows. Deterministic constants; no real data."""
    return _result(
        req,
        {"rows": FINANCE_LOOKUP_ROWS, "count": len(FINANCE_LOOKUP_ROWS)},
        ["src:manifest"],
    )


def finance_export(req: ToolCallRequest, fixtures: LoadedFixtures) -> ToolResult:
    """Sensitive sink — always simulated, never writes anything."""
    return _result(req, dict(FINANCE_EXPORT_RESULT), ["src:manifest"])


TOOL_IMPLS = {
    "document.read": document_read,
    "document.summarize": document_summarize,
    "finance.lookup": finance_lookup,
    "finance.export": finance_export,
}
