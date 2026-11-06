"""Boundary Cartographer — FastAPI application entrypoint (S-01 placeholder)."""

from fastapi import FastAPI

app = FastAPI(
    title="Boundary Cartographer",
    version="0.1.0",
    description="Offline MVP: deterministic policy gate demo (placeholder health endpoint).",
)


@app.get("/api/v1/health")
def health() -> dict:
    """Placeholder health endpoint required by S-01 acceptance."""
    return {"status": "ok", "service": "boundary-cartographer", "version": "0.1.0"}
