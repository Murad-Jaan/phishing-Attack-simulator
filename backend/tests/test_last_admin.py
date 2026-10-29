import threading

from sqlalchemy import text

from app.core.security import hash_password
from app.models.user import UserRole


def _login_admin(client, email):
    c = client.get("/api/v1/auth/csrf")
    token = c.json()["csrf_token"]
    r = client.post("/auth/login", json={"email": email, "password": "pass123456"}, headers={"X-CSRF-Token": token})
    assert r.status_code == 200, r.text


def test_demote_last_admin_returns_409(db_session, client_factory, user_factory):
    admin = user_factory(email="admin@example.com", role=UserRole.ADMIN)
    admin.password_hash = hash_password("pass123456")
    db_session.commit()
    _login_admin(client_factory, "admin@example.com")
    r = client_factory.patch(f"/users/{admin.id}", json={"role": "analyst"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "last_admin_guard"


def test_deactivate_last_admin_returns_409(db_session, client_factory, user_factory):
    admin = user_factory(email="admin2@example.com", role=UserRole.ADMIN)
    admin.password_hash = hash_password("pass123456")
    db_session.commit()
    _login_admin(client_factory, "admin2@example.com")
    r = client_factory.patch(f"/users/{admin.id}", json={"is_active": False})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "last_admin_guard"


def test_self_demotion_covered(db_session, client_factory, user_factory):
    admin = user_factory(email="admin3@example.com", role=UserRole.ADMIN)
    admin.password_hash = hash_password("pass123456")
    db_session.commit()
    _login_admin(client_factory, "admin3@example.com")
    r = client_factory.patch(f"/users/{admin.id}", json={"role": "analyst"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "last_admin_guard"


def test_concurrency_two_demotions_only_one_succeeds(test_engine, db_session):
    """True race: two threads, each with its own app DB session, demote two admins."""
    import uuid
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session
    from app.db import get_db
    from app.main import app
    from app.core.redis import get_redis

    suffix = uuid.uuid4().hex[:8]
    slug = f"conc-org-{suffix}"
    with test_engine.begin() as conn:
        org = conn.execute(
            text(
                "INSERT INTO organizations (name, slug, primary_domain, is_demo) "
                "VALUES (:n, :s, :d, false) RETURNING id"
            ),
            {"n": f"Conc {suffix}", "s": slug, "d": f"{slug}.example.test"},
        ).scalar_one()
        for i in (1, 2):
            conn.execute(
                text(
                    "INSERT INTO users (org_id, email, password_hash, display_name, role, is_active) "
                    "VALUES (:o, :e, :p, 'Test User', 'admin', true)"
                ),
                {
                    "o": org,
                    "e": f"a{i}-{suffix}@example.com",
                    "p": hash_password("pass123456"),
                },
            )
    admin_ids = [
        str(r[0])
        for r in db_session.execute(
            text("SELECT id FROM users WHERE org_id = :o ORDER BY email"), {"o": org}
        ).fetchall()
    ]

    def override():
        db = Session(bind=test_engine)
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    r = get_redis()
    for k in list(r.keys("rl:*")) + list(r.keys("lock:*")):
        r.delete(k)
    client1 = TestClient(app)
    client2 = TestClient(app)
    results = []

    try:
        for i, cli in ((1, client1), (2, client2)):
            c = cli.get("/api/v1/auth/csrf")
            token = c.json()["csrf_token"]
            rl = cli.post(
                "/auth/login",
                json={"email": f"a{i}-{suffix}@example.com", "password": "pass123456"},
                headers={"X-CSRF-Token": token},
            )
            assert rl.status_code == 200, rl.text

        def t1():
            results.append(
                client1.patch(f"/users/{admin_ids[0]}", json={"role": "analyst"}).status_code
            )

        def t2():
            results.append(
                client2.patch(f"/users/{admin_ids[1]}", json={"role": "analyst"}).status_code
            )

        th1 = threading.Thread(target=t1)
        th2 = threading.Thread(target=t2)
        th1.start()
        th2.start()
        th1.join()
        th2.join()
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert results.count(409) >= 1, results
    assert results.count(200) <= 1, results
