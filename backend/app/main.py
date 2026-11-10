from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api.v1 import health, auth, users
from app.api.v1 import settings as settings_router
from app.api.v1 import templates as templates_router
from app.core.csp import build_csp
from app.core.errors import generic_exception_handler, validation_exception_handler, http_exception_handler
from app.core.config import settings
import os
import secrets
import uuid

try:
    settings.validate_secrets()
except Exception:
    if os.getenv("ENV") == "production" or os.getenv("APP_ENV") == "production":
        raise

app = FastAPI(title="Phishing Simulation API", version="0.1.0")


@app.middleware("http")
async def add_request_id_and_security_headers(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    env = os.getenv("ENV", "development")
    app_env = os.getenv("APP_ENV", "development")

    if env == "production" or app_env == "production":
        nonce = secrets.token_urlsafe(16)
        request.state.nonce = nonce
        csp = build_csp("production", nonce)
    else:
        csp = build_csp("development")

    response.headers["Content-Security-Policy"] = csp
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Request-ID"] = request_id
    return response


try:
    settings.validate_secrets()
except Exception:
    if settings.ENV == "production" or settings.APP_ENV == "production":
        raise


app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore
try:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore
except Exception:
    pass
app.add_exception_handler(Exception, generic_exception_handler)  # type: ignore


@app.get("/health")
def health_root():
    return health.check_health()


app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(settings_router.router)
app.include_router(templates_router.router)
