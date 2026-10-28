import threading

from fastapi.testclient import TestClient

from app.main import app
from app.core.security import hash_password
from app.models.organization import Organization
from app.models.user import User, UserRole


client = TestClient(app)


def test_demote_last_admin_returns_409(db_session, organization: Organization):
    admin = User(email="admin@example.com", password_hash=hash_password("pass123456"), org_id=organization.id, role=UserRole.ADMIN)
    db_session.add(admin)
    db_session.commit()
    c = client.get("/api/v1/auth/csrf")
    token = c.json()["csrf_token"]
    r = client.post("/auth/login", json={"email": "admin@example.com", "password": "pass123456"}, headers={"X-CSRF-Token": token})
    assert r.status_code == 200
    r = client.patch(f"/users/{admin.id}", json={"role": "user"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "last_admin_guard"


def test_deactivate_last_admin_returns_409(db_session, organization: Organization):
    admin = User(email="admin2@example.com", password_hash=hash_password("pass123456"), org_id=organization.id, role=UserRole.ADMIN)
    db_session.add(admin)
    db_session.commit()
    c = client.get("/api/v1/auth/csrf")
    token = c.json()["csrf_token"]
    r = client.post("/auth/login", json={"email": "admin2@example.com", "password": "pass123456"}, headers={"X-CSRF-Token": token})
    assert r.status_code == 200
    r = client.patch(f"/users/{admin.id}", json={"is_active": False})
    assert r.status_code == 409


def test_self_demotion_covered(db_session, organization: Organization):
    admin = User(email="admin3@example.com", password_hash=hash_password("pass123456"), org_id=organization.id, role=UserRole.ADMIN)
    db_session.add(admin)
    db_session.commit()
    c = client.get("/api/v1/auth/csrf")
    token = c.json()["csrf_token"]
    r = client.post("/auth/login", json={"email": "admin3@example.com", "password": "pass123456"}, headers={"X-CSRF-Token": token})
    assert r.status_code == 200
    r = client.patch(f"/users/{admin.id}", json={"role": "user"})
    assert r.status_code == 409


def test_concurrency_two_demotions_only_one_succeeds(db_session, organization: Organization):
    admin1 = User(email="a1@example.com", password_hash=hash_password("pass123456"), org_id=organization.id, role=UserRole.ADMIN)
    admin2 = User(email="a2@example.com", password_hash=hash_password("pass123456"), org_id=organization.id, role=UserRole.ADMIN)
    db_session.add_all([admin1, admin2])
    db_session.commit()
    c = client.get("/api/v1/auth/csrf")
    token = c.json()["csrf_token"]
    r = client.post("/auth/login", json={"email": "a1@example.com", "password": "pass123456"}, headers={"X-CSRF-Token": token})
    assert r.status_code == 200
    results = []
    def t1():
        results.append(client.patch(f"/users/{admin1.id}", json={"role": "user"}).status_code)
    def t2():
        results.append(client.patch(f"/users/{admin2.id}", json={"role": "user"}).status_code)
    th1 = threading.Thread(target=t1)
    th2 = threading.Thread(target=t2)
    th1.start()
    th2.start()
    th1.join()
    th2.join()
    # at most one should succeed (200), others 409
    assert results.count(409) >= 1
