"""Boundary Cartographer — FastAPI application (BE-11).

App factory `create_app()` wires CORS (frontend dev origin
http://localhost:5173), the /api/v1 routers, the contract error envelope,
`/api/v1/openapi.json` (parsed from the frozen contract/openapi.yaml) and the
static `/openapi.yaml` file. `make backend` runs `uvicorn app.main:app`.
"""

from pathlib import Path

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.api.errors import register_error_handlers
from app.api.routes_runs import router as runs_router
from app.api.routes_scenarios import router as scenarios_router
from app.policy import load_policy

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_YAML = REPO_ROOT / "contract" / "openapi.yaml"
FRONTEND_DEV_ORIGIN = "http://localhost:5173"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Boundary Cartographer",
        version="1.0.0",
        description="Offline MVP: deterministic policy gate demo. Fully offline after bootstrap.",
        docs_url=None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[FRONTEND_DEV_ORIGIN],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(scenarios_router, prefix="/api/v1")
    app.include_router(runs_router, prefix="/api/v1")

    @app.get("/api/v1/health")
    def health() -> dict:
        return {
            "status": "ok",
            "offline": True,
            "policy_engine": load_policy().engine,
        }

    @app.get("/api/v1/openapi.json", include_in_schema=False)
    def openapi_json() -> JSONResponse:
        spec = yaml.safe_load(OPENAPI_YAML.read_text(encoding="utf-8"))
        return JSONResponse(spec)

    @app.get("/openapi.yaml", include_in_schema=False)
    def openapi_yaml() -> Response:
        return Response(
            content=OPENAPI_YAML.read_text(encoding="utf-8"),
            media_type="application/yaml",
        )

    return app


app = create_app()
