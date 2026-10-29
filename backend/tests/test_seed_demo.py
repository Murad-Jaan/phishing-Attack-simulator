import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core import rate_limit
from app.core.redis import get_redis
from app.core.security import verify_password
from app.models import AuditLog, Organization, User, UserRole
from app.scripts.seed_dev import seed_dev
from app.scripts.unlock_user import unlock_user
BACKEND_DIR = Path(__file__).resolve().parent.parent
TEST_REDIS_DB = 15


@pytest.fixture(autouse=True)
def _use_redis_db15():
    r = get_redis()
    r.execute_command("SELECT", str(TEST_REDIS_DB))
    for pattern in ("rl:*", "lock:*"):
        for k in list(r.keys(pattern)):
            r.delete(k)
    yield r
    for pattern in ("rl:*", "lock:*"):
        for k in list(r.keys(pattern)):
            r.delete(k)
    r.execute_command("SELECT", "0")


def test_seed_refuses_in_production_env_var():
    env = os.environ.copy()
    env["ENV"] = "production"
    env["APP_ENV"] = "development"
    result = subprocess.run(
        [sys.executable, "-m", "app.scripts.seed_dev"],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "production" in result.stdout.lower()


def test_seed_fails_missing_password(db_session, monkeypatch, capsys):
    monkeypatch.delenv("DEMO_ADMIN_1_PASSWORD", raising=False)
    monkeypatch.setenv("DEMO_ADMIN_2_PASSWORD", "strong-pass-123")
    with pytest.raises(SystemExit) as exc:
        seed_dev(db_session)
    assert exc.value.code == 1
    assert "DEMO_ADMIN_1_PASSWORD" in capsys.readouterr().out


def test_seed_fails_short_password(db_session, monkeypatch, capsys):
    monkeypatch.setenv("DEMO_ADMIN_1_PASSWORD", "short-pass1")
    monkeypatch.setenv("DEMO_ADMIN_2_PASSWORD", "strong-pass-123")
    with pytest.raises(SystemExit) as exc:
        seed_dev(db_session)
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "DEMO_ADMIN_1_PASSWORD" in out
    assert "12" in out


def test_seed_creates_demo_org_and_admins(db_session, monkeypatch, organization):
    monkeypatch.setenv("DEMO_ADMIN_1_PASSWORD", "demo-password-1")
    monkeypatch.setenv("DEMO_ADMIN_2_PASSWORD", "demo-password-2")
    seed_dev(db_session)
    org = db_session.execute(
        select(Organization).where(Organization.slug == "demo-org")
    ).scalar_one()
    assert org.name == "Demo Organization"
    assert org.primary_domain == "example.test"
    assert org.is_demo is True
    for num in (1, 2):
        u = db_session.execute(
            select(User).where(User.email == f"demo-admin-{num}@example.test")
        ).scalar_one()
        assert u.org_id == org.id
        assert u.role == UserRole.ADMIN
        assert u.is_demo is True
        assert u.display_name == f"Demo Admin {num}"
        assert u.is_active is True
        assert verify_password(u.password_hash, f"demo-password-{num}")


def test_seed_is_idempotent(db_session, monkeypatch):
    monkeypatch.setenv("DEMO_ADMIN_1_PASSWORD", "demo-password-1")
    monkeypatch.setenv("DEMO_ADMIN_2_PASSWORD", "demo-password-2")
    seed_dev(db_session)
    u1 = db_session.execute(select(User).where(User.email == "demo-admin-1@example.test")).scalar_one()
    u2 = db_session.execute(select(User).where(User.email == "demo-admin-2@example.test")).scalar_one()
    hash1_before, hash2_before = u1.password_hash, u2.password_hash
    u1.is_active = False
    db_session.commit()
    active_before = (u1.is_active, u2.is_active)
    seed_dev(db_session)
    u1 = db_session.execute(select(User).where(User.email == "demo-admin-1@example.test")).scalar_one()
    u2 = db_session.execute(select(User).where(User.email == "demo-admin-2@example.test")).scalar_one()
    assert u1.password_hash == hash1_before
    assert u2.password_hash == hash2_before
    assert (u1.is_active, u2.is_active) == active_before
    org = db_session.execute(select(Organization).where(Organization.slug == "demo-org")).scalar_one()
    cnt = db_session.execute(
        select(func.count(User.id)).where(User.org_id == org.id)
    ).scalar_one()
    assert cnt == 2
    orgs = db_session.execute(
        select(func.count(Organization.id)).where(Organization.slug == "demo-org")
    ).scalar_one()
    assert orgs == 1


def test_unlock_clears_redis_keys_and_writes_one_audit_row(db_session, user_factory, organization, capsys):
    user = user_factory(email="locked@example.test", role=UserRole.ADMIN)
    r = get_redis()
    for _ in range(5):
        res = rate_limit.check_rate_limit(r, "10.9.9.9", "locked@example.test")
        assert res.allowed
        rate_limit.record_fail(r, "locked@example.test")
    assert not rate_limit.check_rate_limit(r, "10.9.9.9", "locked@example.test").allowed
    lk = rate_limit.lock_key("locked@example.test")
    ak = rate_limit.account_key("locked@example.test")
    assert bool(r.exists(lk))
    assert bool(r.exists(f"{lk}:cnt"))
    assert bool(r.exists(ak))
    before_count = db_session.execute(
        select(func.count(AuditLog.id)).where(AuditLog.action == "user.unlock")
    ).scalar_one()
    unlock_user(db_session, "locked@example.test")
    out = capsys.readouterr().out
    assert "unlocked" in out.lower()
    assert not r.exists(lk)
    assert not r.exists(f"{lk}:cnt")
    assert not r.exists(ak)
    after_count = db_session.execute(
        select(func.count(AuditLog.id)).where(AuditLog.action == "user.unlock")
    ).scalar_one()
    assert after_count == before_count + 1
    row = db_session.execute(
        select(AuditLog).where(AuditLog.action == "user.unlock").order_by(AuditLog.id.desc())
    ).scalar_one()
    assert row.entity_id == str(user.id)
    assert row.org_id == user.org_id
    assert row.before is None
    assert row.after == {"is_active": True}
    assert row.reason is None
    blob = json.dumps({"before": row.before, "after": row.after}).lower()
    assert "password" not in blob
    assert "token" not in blob
    assert "hash" not in blob
    assert user.password_hash not in blob
    assert "password" not in out.lower()
    assert user.password_hash not in out
    assert "token" not in out.lower()


def test_unlock_unknown_email_fails_without_leaking(db_session, capsys):
    with pytest.raises(SystemExit) as exc:
        unlock_user(db_session, "ghost-user-no-leak@example.test")
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "not found" in out.lower()
    assert "ghost-user-no-leak" not in out


def test_unlock_empty_email_fails_clearly(db_session, capsys):
    with pytest.raises(SystemExit) as exc:
        unlock_user(db_session, "")
    assert exc.value.code == 1
    assert "EMAIL is required" in capsys.readouterr().out


def test_unlock_missing_env_fails_clearly(db_session, monkeypatch, capsys):
    monkeypatch.delenv("UNLOCK_EMAIL", raising=False)
    with pytest.raises(SystemExit) as exc:
        unlock_user(db_session)
    assert exc.value.code == 1
    assert "EMAIL is required" in capsys.readouterr().out
