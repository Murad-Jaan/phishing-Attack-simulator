from __future__ import annotations

import os

from redis import Redis

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is not None:
        return _redis
    url = os.getenv("REDIS_URL") or "redis://redis:6379/0"
    _redis = Redis.from_url(url, decode_responses=True)
    return _redis
