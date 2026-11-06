"""Run endpoints (BE-11).

- POST /api/v1/runs               -> 201, runs the offline analysis synchronously
                                    and persists the run + evidence chain + pending
                                    approval items.
- GET  /api/v1/runs/{run_id}      -> 200 stored payload (byte-identical), 404 RUN_NOT_FOUND.
- POST /api/v1/runs/{run_id}/approval -> records a decision ONLY (never applies it,
                                    never calls a tool); 409 on repeat.
"""

import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import get_db
from app.api.errors import ApiError
from app.contracts import ErrorCode
from app.fixtures import load_fixtures
from app.orchestrator.run import run_analysis
from app.store import repository

router = APIRouter(prefix="/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    options: "CreateRunOptions | None" = None


class CreateRunOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    include_disproved: bool


class ApprovalDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: str
    decision: Literal["approve", "reject"]
    decided_by: str | None = None
    note: str | None = Field(default=None)


def _persist_run(conn: sqlite3.Connection, run: dict) -> None:
    repository.insert_run(conn, run)
    # Replay event IDs restart per path, so evidence_ids can repeat within one
    # run; suffix occurrences to satisfy the evidence table's uniqueness while
    # leaving the returned run payload untouched.
    seen: dict[str, int] = {}
    for record in run["evidence"]:
        eid = record["evidence_id"]
        seen[eid] = seen.get(eid, 0) + 1
        stored = dict(record)
        if seen[eid] > 1:
            stored["evidence_id"] = f"{eid}#{seen[eid]}"
        repository.append_evidence(conn, run["run_id"], stored)
    for item in run["approval"]["items"]:
        if item["status"] == "pending":
            repository.create_approval_item(conn, run["run_id"], item)


@router.post("", status_code=201)
def create_run(
    body: CreateRunRequest, response: Response, conn: sqlite3.Connection = Depends(get_db)
) -> dict:
    fixtures = load_fixtures()
    if body.scenario_id != fixtures.scenario_id:
        raise ApiError(
            400, ErrorCode.SCENARIO_NOT_FOUND,
            f"scenario '{body.scenario_id}' not found", {"scenario_id": body.scenario_id},
        )
    run = run_analysis(body.scenario_id)
    payload = run.model_dump(by_alias=True, mode="json")
    _persist_run(conn, payload)
    response.status_code = 201
    return payload


@router.get("/{run_id}")
def get_run(run_id: str, conn: sqlite3.Connection = Depends(get_db)) -> Response:
    raw = repository.get_run_raw(conn, run_id)
    if raw is None:
        raise ApiError(404, ErrorCode.RUN_NOT_FOUND, "run not found", {"run_id": run_id})
    # Return the stored canonical bytes so GET is byte-identical to the stored payload.
    return Response(content=raw, media_type="application/json")


@router.post("/{run_id}/approval")
def decide_approval(
    run_id: str, body: ApprovalDecisionRequest, conn: sqlite3.Connection = Depends(get_db)
) -> dict:
    if repository.get_run(conn, run_id) is None:
        raise ApiError(404, ErrorCode.RUN_NOT_FOUND, "run not found", {"run_id": run_id})
    try:
        repository.decide_approval(
            conn, run_id, body.approval_id, body.decision,
            decided_by=body.decided_by, note=body.note,
        )
    except KeyError:
        raise ApiError(
            404, ErrorCode.RUN_NOT_FOUND,
            f"approval '{body.approval_id}' not found for run '{run_id}'",
            {"run_id": run_id, "approval_id": body.approval_id},
        ) from None
    except repository.ApprovalConflict as exc:
        state = repository.get_approval_state(conn, run_id)
        item = next(i for i in state["items"] if i["approval_id"] == body.approval_id)
        raise ApiError(
            409, ErrorCode.APPROVAL_ALREADY_DECIDED, str(exc),
            {"approval_id": body.approval_id, "status": item["status"]},
        ) from None
    return repository.get_approval_state(conn, run_id)
