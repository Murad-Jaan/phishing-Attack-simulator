from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def error_payload(request: Request, code: str, message: str, fields: dict) -> dict:
    rid = getattr(getattr(request, "state", object()), "request_id", None)
    return {"error": {"code": code, "message": message, "fields": fields, "request_id": rid}}


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=error_payload(request, "validation_error", "Invalid request", {}),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=error_payload(request, "internal_error", "Internal server error", {}),
    )


async def http_exception_handler(request: Request, exc):
    detail = getattr(exc, "detail", "http_error")
    code = "http_error"
    if isinstance(detail, str) and detail in ("unauthenticated", "forbidden", "rate_limited", "csrf_failed", "invalid_credentials"):
        code = detail
    headers = getattr(exc, "headers", None)
    return JSONResponse(
        status_code=getattr(exc, "status_code", 400),
        content=error_payload(request, code, str(detail) if isinstance(detail, str) else "Error", {}),
        headers=headers,
    )
