from sqlalchemy import text

from app.core.security import hash_password
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.main import app
from fastapi.testclient import TestClient


client = TestClient(app)


def test_audit_rows_created_and_no_secrets(db_session, organization: Organization):
    user = User(email="audit@example.com", password_hash=hash_password("pass123456"), org_id=organization.id, role=UserRole.EMPLOYEE, display_name='u')
    db_session.add(user)
    db_session.commit()
    c = client.get("/api/v1/auth/csrf")
    token = c.json()["csrf_token"]
    r = client.post("/auth/login", json={"email": "audit@example.com", "password": "pass123456"}, headers={"X-CSRF-Token": token})
    assert r.status_code == 200
    # failure
    c2 = client.get("/api/v1/auth/csrf")
    token2 = c2.json()["csrf_token"]
    r2 = client.post("/auth/login", json={"email": "audit@example.com", "password": "wrong"}, headers={"X-CSRF-Token": token2})
    assert r2.status_code == 401
    # logout
    client.post("/auth/logout", headers={"X-CSRF-Token": token2})
    # check rows
    rows = db_session.execute(text("SELECT action, before, after FROM audit_log")).fetchall()
    actions = [x[0] for x in rows]
    assert "auth.login" in actions
    for x in rows:
        s = str(x[1]) + str(x[2])
        assert "pass123456" not in s
        assert "token" not in s.lower() or '"token"' not in s.lower()
        assert "csrf" not in s.lower()
