from app.core.security import hash_password
from app.models.user import UserRole


def test_users_401_unauthenticated(client_factory):
    r = client_factory.get("/users")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"
    r = client_factory.patch("/users/someid", json={"role": "analyst"})
    assert r.status_code == 401


def test_users_403_wrong_role(db_session, client_factory, user_factory):
    u = user_factory(email="u@example.com", role=UserRole.EMPLOYEE)
    u.password_hash = hash_password("pass123456")
    db_session.commit()
    r = client_factory.get("/api/v1/auth/csrf")
    token = r.json()["csrf_token"]
    r2 = client_factory.post("/auth/login", json={"email": "u@example.com", "password": "pass123456"}, headers={"X-CSRF-Token": token})
    assert r2.status_code == 200, r2.text
    r3 = client_factory.get("/users")
    assert r3.status_code == 403
    assert r3.json()["error"]["code"] == "forbidden"
    r4 = client_factory.patch("/users/123", json={"role": "analyst"})
    assert r4.status_code == 403
