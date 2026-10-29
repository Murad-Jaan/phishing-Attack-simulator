from __future__ import annotations

import hmac
import hashlib
from typing import cast

from fastapi import Request
from redis import Redis

from app.core.config import settings


class RateLimitResult:
    def __init__(self, allowed: bool, retry_after: int | None = None):
        self.allowed = allowed
        self.retry_after = retry_after


def _hmac_key(salt: str) -> str:
    key = getattr(settings, "SECRET_KEY", None) or getattr(settings, "SESSION_SECRET", None) or getattr(settings, "CSRF_SECRET", "")
    return hmac.new(str(key).encode(), salt.encode(), hashlib.sha256).hexdigest()


def account_key(email: str) -> str:
    h = _hmac_key(f"acct:{email.lower()}")
    return f"rl:acct:{h}"


def ip_key(ip: str) -> str:
    h = _hmac_key(f"ip:{ip}")
    return f"rl:ip:{h}"


def lock_key(email: str) -> str:
    h = _hmac_key(f"lock:{email.lower()}")
    return f"lock:acct:{h}"


def _get_redis() -> Redis | None:
    try:
        from app.core.redis import get_redis

        r = get_redis()
        return r
    except Exception:
        return None


def check_rate_limit(redis_client: Redis, ip: str, email: str) -> RateLimitResult:
    window = 900  # 15m
    ak = account_key(email)
    ik = ip_key(ip)
    lk = lock_key(email)
    try:
        lk_ttl = int(cast(int, redis_client.ttl(lk)))
        if lk_ttl and lk_ttl > 0:
            return RateLimitResult(False, lk_ttl)
        a = int(cast(int, redis_client.incr(ak)))
        if a == 1:
            redis_client.expire(ak, window)
        if a > 5:
            ra = int(cast(int, redis_client.ttl(ak)))
            return RateLimitResult(False, ra if ra and ra > 0 else window)
        i = int(cast(int, redis_client.incr(ik)))
        if i == 1:
            redis_client.expire(ik, window)
        if i > 20:
            ra = int(cast(int, redis_client.ttl(ik)))
            return RateLimitResult(False, ra if ra and ra > 0 else window)
        return RateLimitResult(True)
    except Exception:
        return RateLimitResult(False, 60)


def record_fail(redis_client: Redis, email: str) -> None:
    lk = lock_key(email)
    try:
        cnt = int(cast(int, redis_client.incr(f"{lk}:cnt")))
        if cnt == 1:
            redis_client.expire(f"{lk}:cnt", 3600)
        if cnt >= 5:
            ttl = min(60 * (2 ** (cnt - 5)), 3600)
            redis_client.setex(lk, ttl, "1")
    except Exception:
        pass


def record_success(redis_client: Redis, email: str) -> None:
    lk = lock_key(email)
    try:
        redis_client.delete(lk)
        redis_client.delete(f"{lk}:cnt")
        redis_client.delete(account_key(email))
    except Exception:
        pass


def clear_lockouts_for_email(redis_client: Redis, email: str) -> None:
    lk = lock_key(email)
    try:
        redis_client.delete(lk)
        redis_client.delete(f"{lk}:cnt")
    except Exception:
        pass


def check_rate_limit_request(request: Request, email: str) -> RateLimitResult:
    r = _get_redis()
    if r is None:
        return RateLimitResult(False, 60)
    ip = getattr(request.state, "client_ip", None) or (request.client.host if request.client else "")
    return check_rate_limit(r, ip, email)


def record_fail_for(email: str) -> None:
    r = _get_redis()
    if r is None:
        return
    record_fail(r, email)


def record_success_for(email: str) -> None:
    r = _get_redis()
    if r is None:
        return
    record_success(r, email)
