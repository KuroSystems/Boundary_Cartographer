"""Typed orchestrator messages (BE-09) — matching docs/roles.md.

All Pydantic v2 with extra="forbid"; no free-text/instruction fields — every
field is structured and validated. Malformed messages raise ValidationError.
"""

from pydantic import BaseModel, ConfigDict, Field


class Msg(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---- Inventory ----
class InventoryRequest(Msg):
    scenario_id: str


class InventoryReport(Msg):
    scenario: dict  # ScenarioResponse payload (validated on parse)
    input_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


# ---- Path Finder ----
class PathFindRequest(Msg):
    graph: dict  # contract Graph payload
    origin: str
    sinks: list[str]
    max_hops: int = 5


class PathFindReport(Msg):
    paths: list[dict]  # contract Path payloads (candidate/disproved only)


# ---- Injection Tester ----
class ReplayRequest(Msg):
    paths: list[dict]


class ReplayReport(Msg):
    replay_events: list[dict]  # contract ReplayEvent payloads
    path_event_map: dict[str, list[str]] = {}  # path_id -> event_ids (attribution)


# ---- Policy Verifier ----
class VerifyRequest(Msg):
    paths: list[dict]
    replay_events: list[dict]


class VerifyReport(Msg):
    paths: list[dict]  # Path payloads with final verifier-assigned statuses


# ---- Evidence Writer ----
class EvidenceRequest(Msg):
    run_id: str
    scenario_id: str
    graph: dict
    paths: list[dict]
    replay_events: list[dict]
    input_digest: str


class EvidenceReport(Msg):
    run: dict  # full RunResponse payload
