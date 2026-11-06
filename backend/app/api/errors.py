"""Error envelope + exception handlers (BE-11).

Every error response matches the frozen contract ErrorResponse schema:
{ "error": { "code": <ErrorCode>, "message": str, "details": object } }.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.contracts import ErrorCode


class ApiError(Exception):
    """Domain error mapped to a contract ErrorResponse."""

    def __init__(self, status: int, code: ErrorCode, message: str, details: dict | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}


def error_payload(code: ErrorCode, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code.value, "message": message, "details": details or {}}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error_handler(_req: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status, content=error_payload(exc.code, exc.message, exc.details)
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_req: Request, exc: RequestValidationError) -> JSONResponse:
        issues = [
            f"{'.'.join(str(loc) for loc in err['loc'] if loc != 'body') or 'body'}: {err['msg']}"
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=error_payload(
                ErrorCode.VALIDATION_ERROR, "request body failed validation", {"issues": issues}
            ),
        )
