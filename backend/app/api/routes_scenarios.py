"""Scenario endpoints (BE-11): GET /api/v1/scenarios/demo.

Read-only: returns the seeded demo scenario payload assembled by the fixture
loader. No run, no side effects.
"""

from fastapi import APIRouter

from app.fixtures import load_fixtures

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("/demo")
def get_demo_scenario() -> dict:
    fixtures = load_fixtures()
    return fixtures.scenario_response().model_dump(by_alias=True, mode="json")
