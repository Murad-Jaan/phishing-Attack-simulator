from fastapi import APIRouter
from fastapi.responses import JSONResponse
import os
import psycopg
import redis

router = APIRouter()


def check_health():
    db_status = "ok"
    redis_status = "ok"
    overall_status = "ok"
    status_code = 200
    
    try:
        db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://phish:phishpass@postgres:5432/phishsim")
        if "postgresql+psycopg://" in db_url:
            db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
        conn = psycopg.connect(db_url, connect_timeout=2)
        conn.close()
    except Exception:
        db_status = "down"
        overall_status = "degraded"
        status_code = 503
    
    try:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        r = redis.from_url(redis_url, socket_connect_timeout=2)
        r.ping()
        r.close()
    except Exception:
        redis_status = "down"
        overall_status = "degraded"
        status_code = 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall_status,
            "app": "phishsim-api",
            "database": db_status,
            "redis": redis_status,
        }
    )


@router.get("/health")
def health():
    return check_health()
