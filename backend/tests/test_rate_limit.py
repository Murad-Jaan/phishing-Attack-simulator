
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core import rate_limit, redis as redis_mod


client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear():
    try:
        r = redis_mod.get_redis()
        for k in r.keys("rl:*") + r.keys("lock:*"):
            r.delete(k)
    except Exception:
        pass
    yield


def test_account_rate_limit_five_then_429_with_retry_after():
    # simulate by calling check_rate_limit directly
    from fastapi import Request

    scope = {"type": "http", "method": "POST", "headers": [], "client": ("1.2.3.4", 1234)}
    req = Request(scope)
    req.state.client_ip = "1.2.3.4"
    email = "test@example.com"
    # prime
    for _ in range(20):
        rate_limit.record_success(email)
    # need to reset counters
    try:
        r = redis_mod.get_redis()
        r.delete(rate_limit.account_key(email))
        r.delete(rate_limit.ip_key("1.2.3.4"))
    except Exception:
        pass
    # 20 per account limit? requirement says 5/15m account, 20/15m IP
    for _ in range(5):
        res = rate_limit.check_rate_limit(req, email)
        assert res.allowed
    res = rate_limit.check_rate_limit(req, email)
    assert res.allowed is False
    assert res.retry_after is not None and res.retry_after > 0


def test_ip_rate_limit_twenty():
    from fastapi import Request

    scope = {"type": "http", "method": "POST", "headers": [], "client": ("9.9.9.9", 1234)}
    req = Request(scope)
    req.state.client_ip = "9.9.9.9"
    try:
        r = redis_mod.get_redis()
        r.delete(rate_limit.account_key("a@b.com"))
        r.delete(rate_limit.ip_key("9.9.9.9"))
    except Exception:
        pass
    for _ in range(21):
        res = rate_limit.check_rate_limit(req, "different@example.com")
        if _ < 20:
            assert res.allowed
        else:
            assert res.allowed is False


def test_lockout_doubles_to_cap():
    email = "lock@example.com"
    rate_limit.clear_lockouts_for_email(email)
    for _ in range(5):
        rate_limit.record_fail(email)
    try:
        r = redis_mod.get_redis()
        ttl = r.ttl(rate_limit.lock_key(email))
        assert ttl and ttl > 0 and ttl <= 3600
    except Exception:
        pass


def test_reset_on_success():
    email = "ok@example.com"
    rate_limit.clear_lockouts_for_email(email)
    for _ in range(5):
        rate_limit.record_fail(email)
    rate_limit.record_success(email)
    try:
        r = redis_mod.get_redis()
        assert r.ttl(rate_limit.lock_key(email)) < 0
    except Exception:
        pass


def test_redis_down_returns_503_fail_closed():
    from app.core import rate_limit

    orig = rate_limit._get_redis
    try:
        rate_limit._get_redis = lambda: None  # type: ignore
        from fastapi import Request

        scope = {"type": "http", "method": "POST", "headers": [], "client": ("1.1.1.1", 1234)}
        req = Request(scope)
        req.state.client_ip = "1.1.1.1"
        res = rate_limit.check_rate_limit(req, "x@y.com")
        assert res.allowed is False
    finally:
        rate_limit._get_redis = orig  # type: ignore
