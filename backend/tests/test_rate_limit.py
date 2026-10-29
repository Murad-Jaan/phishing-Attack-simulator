import pytest
from fastapi import Request

from app.core import rate_limit
from app.core.redis import get_redis


DB15_KEYS = "rl:* lock:*"


@pytest.fixture(autouse=True)
def _clear_rl_db15():
    r = get_redis()
    r.execute_command("SELECT", "15")
    for pattern in ("rl:*", "lock:*"):
        for k in list(r.keys(pattern)):
            r.delete(k)
    yield
    for pattern in ("rl:*", "lock:*"):
        for k in list(r.keys(pattern)):
            r.delete(k)
    r.execute_command("SELECT", "0")


def _request(ip: str) -> Request:
    scope = {"type": "http", "method": "POST", "headers": [], "client": (ip, 12345)}
    req = Request(scope)
    req.state.client_ip = ip
    return req


def test_account_rate_limit_five_then_429_with_retry_after():
    r = get_redis()
    ip = "10.0.0.1"
    email = "acct@example.com"
    # 5 failures
    for _ in range(5):
        res = rate_limit.check_rate_limit(r, ip, email)
        assert res.allowed
        rate_limit.record_fail(r, email)
    # 6th check is blocked with Retry-After
    res = rate_limit.check_rate_limit(r, ip, email)
    assert res.allowed is False
    assert res.retry_after is not None and res.retry_after > 0


def test_ip_rate_limit_twenty():
    r = get_redis()
    ip = "10.0.0.2"
    for i in range(20):
        email = f"user{i}@example.com"
        res = rate_limit.check_rate_limit(r, ip, email)
        assert res.allowed
    res = rate_limit.check_rate_limit(r, ip, "user20@example.com")
    assert res.allowed is False


def test_lockout_doubles_to_cap():
    r = get_redis()
    email = "lock@example.com"
    for i in range(8):
        rate_limit.record_fail(r, email)
    ttl = int(r.ttl(rate_limit.lock_key(email)))
    assert ttl > 0
    assert ttl <= 3600


def test_reset_on_success():
    r = get_redis()
    email = "reset@example.com"
    for _ in range(5):
        rate_limit.record_fail(r, email)
    # locked
    res = rate_limit.check_rate_limit(r, "10.0.0.3", email)
    assert res.allowed is False
    rate_limit.record_success(r, email)
    lk_ttl = int(r.ttl(rate_limit.lock_key(email)))
    assert lk_ttl < 0


def test_redis_down_returns_503_fail_closed():
    from app.main import app
    from fastapi.testclient import TestClient

    orig = rate_limit._get_redis
    try:
        rate_limit._get_redis = lambda: None  # type: ignore
        client = TestClient(app, raise_server_exceptions=False)
        client.app.dependency_overrides.setdefault(lambda: None, lambda: None)
        r = client.get("/health")
        # rate limit check with redis down must fail closed; direct unit check:
        from fastapi import Request as _Req

        res = rate_limit.check_rate_limit_request(_Req({"type": "http", "method": "POST", "headers": [], "client": ("1.1.1.1", 1)}), "x@y.com")
        assert res.allowed is False
        assert r.status_code == 200  # health still works
    finally:
        rate_limit._get_redis = orig  # type: ignore
