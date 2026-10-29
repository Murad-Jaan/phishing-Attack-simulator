import pytest

from app.core.redis import get_redis
from app.core.security import hash_password


@pytest.fixture(autouse=True)
def _clear_rl():
    try:
        r = get_redis()
        for k in list(r.keys("rl:*")) + list(r.keys("lock:*")):
            r.delete(k)
    except Exception:
        pass
    yield


def test_csrf_endpoint(client_factory):
    r = client_factory.get("/api/v1/auth/csrf")
    assert r.status_code == 200
    assert "csrf_token" in r.json()


def test_login_success_sets_both_cookies_with_flags(db_session, client_factory, user_factory):
    user_factory(email="login@example.com")
    user = db_session.query(__import__("app.models.user", fromlist=["User"]).User).filter_by(email="login@example.com").one()
    user.password_hash = hash_password("pass123456")
    db_session.commit()
    r = client_factory.get("/api/v1/auth/csrf")
    token = r.json()["csrf_token"]
    r2 = client_factory.post("/auth/login", json={"email": "login@example.com", "password": "pass123456"}, headers={"X-CSRF-Token": token})
    assert r2.status_code == 200, r2.text
    cookies = r2.headers.get_list("set-cookie")
    session_cookies = [x for x in cookies if "phishsim_session" in x]
    csrf_cookies = [x for x in cookies if "phishsim_csrf" in x]
    assert session_cookies, cookies
    assert csrf_cookies, cookies
    sc = session_cookies[0]
    assert "HttpOnly" in sc or "httponly" in sc.lower()
    assert "Path=/" in sc
    assert "SameSite=lax" in sc or "samesite=lax" in sc.lower()
    assert "Domain=" not in sc


def test_login_same_body_for_unknown_and_wrong_password(db_session, client_factory, user_factory):

    u = user_factory(email="known@example.com")
    u.password_hash = hash_password("pass123456")
    db_session.commit()
    r = client_factory.get("/api/v1/auth/csrf")
    token = r.json()["csrf_token"]
    r1 = client_factory.post("/auth/login", json={"email": "unknown@example.com", "password": "unknownpw1"}, headers={"X-CSRF-Token": token})
    r = client_factory.get("/api/v1/auth/csrf")
    token2 = r.json()["csrf_token"]
    r2 = client_factory.post("/auth/login", json={"email": "known@example.com", "password": "wrongpw12"}, headers={"X-CSRF-Token": token2})
    assert r1.status_code == r2.status_code == 401
    j1 = r1.json()
    j2 = r2.json()
    assert j1["error"]["code"] == j2["error"]["code"]
    assert j1["error"]["message"] == j2["error"]["message"]
    assert j1["error"]["fields"] == j2["error"]["fields"]


def test_logout_needs_csrf_403_without(db_session, client_factory, user_factory):

    u = user_factory(email="lo@example.com")
    u.password_hash = hash_password("pass123456")
    db_session.commit()
    r = client_factory.get("/api/v1/auth/csrf")
    token = r.json()["csrf_token"]
    r2 = client_factory.post("/auth/login", json={"email": "lo@example.com", "password": "pass123456"}, headers={"X-CSRF-Token": token})
    assert r2.status_code == 200, r2.text
    r3 = client_factory.post("/auth/logout")
    assert r3.status_code == 403


def test_auth_me_401_without_session(client_factory):
    r = client_factory.get("/auth/me")
    assert r.status_code == 401
