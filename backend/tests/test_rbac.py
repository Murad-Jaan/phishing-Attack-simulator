from fastapi.testclient import TestClient

from app.main import app
from app.core.security import hash_password
from app.models.organization import Organization
from app.models.user import User, UserRole


client = TestClient(app)


def test_users_401_unauthenticated():
    r = client.get("/users")
    assert r.status_code == 401
    r = client.patch("/users/someid", json={"role": "admin"})
    assert r.status_code == 401


def test_users_403_wrong_role(db_session, organization: Organization):
    user = User(email="u@example.com", password_hash=hash_password("pass123456"), org_id=organization.id, role=UserRole.EMPLOYEE, display_name='u')
    db_session.add(user)
    db_session.commit()
    c = client.get("/api/v1/auth/csrf")
    token = c.json()["csrf_token"]
    r = client.post("/auth/login", json={"email": "u@example.com", "password": "pass123456"}, headers={"X-CSRF-Token": token})
    assert r.status_code == 200
    r = client.get("/users")
    assert r.status_code == 403
    r = client.patch("/users/123", json={"role": "admin"})
    assert r.status_code == 403
