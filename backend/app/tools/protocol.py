"""MCP-shaped typed tool boundary protocol (BE-04, ADR-0002).

In-process only: `tools/list` + `tools/call` semantics with
`{name, arguments} -> {content: [{type: "json", data}], is_error, simulated}`.
Every result carries `simulated: true`. No sockets, no MCP SDK, no network.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.contracts import Purpose


class ToolCallRequest(BaseModel):
    """One typed tool invocation (the `tools/call` request shape)."""

    model_config = ConfigDict(extra="forbid")

    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    actor: str
    purpose: Purpose
    taint: list[str] = Field(default_factory=list)


class ToolContentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["json"]
    data: Any


class ToolResult(BaseModel):
    """One typed tool result (the `tools/call` response shape)."""

    model_config = ConfigDict(extra="forbid")

    tool: str
    content: list[ToolContentItem]
    is_error: bool
    simulated: bool
    source_ids: list[str]
    code: str | None = None  # machine-readable error code, e.g. UNKNOWN_TOOL

    @model_validator(mode="after")
    def _enforce_simulated(self) -> "ToolResult":
        # ADR-0002: every tool result is simulated — always.
        if self.simulated is not True:
            raise ValueError("tool results must always have simulated == true")
        return self
