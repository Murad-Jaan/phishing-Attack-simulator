from sqlalchemy import text

from app.core.security import hash_password
from app.models.user import UserRole
from app.core.redis import get_redis


def test_audit_rows_created_and_no_secrets(db_session, client_factory, user_factory):
    try:
        r = get_redis()
        for k in list(r.keys("rl:*")) + list(r.keys("lock:*")):
            r.delete(k)
    except Exception:
        pass
    u = user_factory(email="audit@example.com", role=UserRole.EMPLOYEE)
    u.password_hash = hash_password("pass123456")
    db_session.commit()
    c = client_factory.get("/api/v1/auth/csrf")
    token = c.json()["csrf_token"]
    r = client_factory.post("/auth/login", json={"email": "audit@example.com", "password": "pass123456"}, headers={"X-CSRF-Token": token})
    assert r.status_code == 200, r.text
    c2 = client_factory.get("/api/v1/auth/csrf")
    token2 = c2.json()["csrf_token"]
    r2 = client_factory.post("/auth/login", json={"email": "audit@example.com", "password": "wrongpw12"}, headers={"X-CSRF-Token": token2})
    assert r2.status_code == 401
    client_factory.post("/auth/logout", headers={"X-CSRF-Token": token2})
    rows = db_session.execute(text("SELECT action, before, after FROM audit_log")).fetchall()
    actions = [x[0] for x in rows]
    assert "auth.login" in actions
    for x in rows:
        s = str(x[1]) + str(x[2])
        assert "pass123456" not in s
        assert "wrongpw12" not in s
