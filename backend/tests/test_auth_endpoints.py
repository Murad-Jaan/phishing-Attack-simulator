import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core import redis as redis_mod
from app.core.security import hash_password
from app.models.organization import Organization
from app.models.user import User, UserRole


client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_rl():
    try:
        r = redis_mod.get_redis()
        for k in r.keys("rl:*") + r.keys("lock:*"):
            r.delete(k)
    except Exception:
        pass
    yield


def test_csrf_endpoint(db_session, organization: Organization):
    r = client.get("/api/v1/auth/csrf")
    assert r.status_code == 200
    assert "csrf_token" in r.json()


def test_login_success_sets_both_cookies_with_flags(db_session, organization: Organization):
    user = User(email="login@example.com", password_hash=hash_password("pass123456"), org_id=organization.id, role=UserRole.EMPLOYEE, display_name='u')
    db_session.add(user)
    db_session.commit()
    c = client.get("/api/v1/auth/csrf")
    token = c.json()["csrf_token"]
    client.cookies.update(c.cookies)
    r = client.post("/auth/login", json={"email": "login@example.com", "password": "pass123456"}, headers={"X-CSRF-Token": token})
    assert r.status_code == 200
    cookies = r.headers.get_list("set-cookie")
    assert any("__Host-phishsim_session" in x or "phishsim_session" in x for x in cookies)
    assert any("__Host-phishsim_csrf" in x or "phishsim_csrf" in x for x in cookies)


def test_login_same_body_for_unknown_and_wrong_password(db_session, organization: Organization):
    user = User(email="known@example.com", password_hash=hash_password("pass123456"), org_id=organization.id, role=UserRole.EMPLOYEE, display_name='u')
    db_session.add(user)
    db_session.commit()
    c = client.get("/api/v1/auth/csrf")
    token = c.json()["csrf_token"]
    client.cookies.clear()
    client.cookies.update(c.cookies)
    r1 = client.post("/auth/login", json={"email": "unknown@example.com", "password": "pass123456"}, headers={"X-CSRF-Token": token})
    c2 = client.get("/api/v1/auth/csrf")
    token2 = c2.json()["csrf_token"]
    client.cookies.clear()
    client.cookies.update(c2.cookies)
    r2 = client.post("/auth/login", json={"email": "known@example.com", "password": "wrongpass"}, headers={"X-CSRF-Token": token2})
    assert r1.status_code == r2.status_code
    j1 = r1.json()
    j2 = r2.json()
    assert j1["error"]["code"] == j2["error"]["code"]
    assert j1["error"]["message"] == j2["error"]["message"]


def test_logout_needs_csrf_403_without(db_session, organization: Organization):
    user = User(email="lo@example.com", password_hash=hash_password("pass123456"), org_id=organization.id, role=UserRole.EMPLOYEE, display_name='u')
    db_session.add(user)
    db_session.commit()
    c = client.get("/api/v1/auth/csrf")
    token = c.json()["csrf_token"]
    client.cookies.update(c.cookies)
    r = client.post("/auth/login", json={"email": "lo@example.com", "password": "pass123456"}, headers={"X-CSRF-Token": token})
    assert r.status_code == 200
    client.cookies.update(r.cookies)
    r2 = client.post("/auth/logout")
    assert r2.status_code == 403


def test_auth_me_401_without_session():
    r = client.get("/auth/me")
    assert r.status_code == 401
