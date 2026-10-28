from __future__ import annotations

import hmac
import hashlib
import time
from typing import Optional

from fastapi import Request
from redis import Redis

from app.core.config import settings


class RateLimitResult:
    def __init__(self, allowed: bool, retry_after: int | None = None):
        self.allowed = allowed
        self.retry_after = retry_after


def _hmac_key(salt: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), salt.encode(), hashlib.sha256).hexdigest()


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


def check_rate_limit(request: Request, email: str) -> RateLimitResult:
    r = _get_redis()
    if r is None:
        # fail closed
        return RateLimitResult(False, 60)
    ip = getattr(request.state, "client_ip", None) or (request.client.host if request.client else "")
    now = int(time.time())
    window = 900  # 15m
    ak = account_key(email)
    ik = ip_key(ip)
    lk = lock_key(email)
    try:
        lk_ttl = r.ttl(lk)
        if lk_ttl and lk_ttl > 0:
            return RateLimitResult(False, lk_ttl)
        a = r.incr(ak)
        if a == 1:
            r.expire(ak, window)
        if a > 20:
            ra = r.ttl(ak)
            return RateLimitResult(False, ra if ra and ra > 0 else window)
        i = r.incr(ik)
        if i == 1:
            r.expire(ik, window)
        if i > 20:
            ra = r.ttl(ik)
            return RateLimitResult(False, ra if ra and ra > 0 else window)
        return RateLimitResult(True)
    except Exception:
        return RateLimitResult(False, 60)


def record_fail(email: str) -> None:
    r = _get_redis()
    if r is None:
        return
    lk = lock_key(email)
    try:
        cnt = r.incr(f"{lk}:cnt")
        if cnt == 1:
            r.expire(f"{lk}:cnt", 3600)
        if cnt >= 5:
            # doubling to 1h cap
            ttl = min(60 * (2 ** (cnt - 5)), 3600)
            r.setex(lk, ttl, "1")
    except Exception:
        pass


def record_success(email: str) -> None:
    r = _get_redis()
    if r is None:
        return
    lk = lock_key(email)
    try:
        r.delete(lk)
        r.delete(f"{lk}:cnt")
    except Exception:
        pass


def clear_lockouts_for_email(email: str) -> None:
    r = _get_redis()
    if r is None:
        return
    lk = lock_key(email)
    try:
        r.delete(lk)
        r.delete(f"{lk}:cnt")
    except Exception:
        pass
