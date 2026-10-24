from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import health
from app.core.csp import build_csp
import os
import secrets

app = FastAPI(title="Phishing Simulation API", version="0.1.0")

# CSP middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
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
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health at root path
@app.get("/health")
def health_root():
    return health.check_health()

app.include_router(health.router, prefix="/api/v1")
