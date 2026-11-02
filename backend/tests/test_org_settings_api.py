"""M2 organization settings API: RBAC, CSRF, check order, validation."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.models.user import UserRole
from tests.conftest import login_as, session_csrf_token


def _make_user(db_session, user_factory, email: str, role: UserRole) -> None:
    user = user_factory(email=email, role=role)
    user.password_hash = hash_password("pass123456")
    db_session.commit()


def test_get_settings_unauthenticated_401(client_factory):
    r = client_factory.get("/settings/organization")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"


def test_patch_settings_unauthenticated_401(client_factory):
    r = client_factory.patch(
        "/api/v1/settings/organization", json={"retention_days": 120}
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"


def test_analyst_403_on_get_and_patch(db_session, client_factory, user_factory):
    _make_user(db_session, user_factory, "analyst@example.test", UserRole.ANALYST)
    login_as(client_factory, "analyst@example.test", "pass123456")
    r = client_factory.get("/api/v1/settings/organization")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"
    r2 = client_factory.patch(
        "/api/v1/settings/organization", json={"retention_days": 120}
    )
    assert r2.status_code == 403
    assert r2.json()["error"]["code"] == "forbidden"


def test_employee_403_on_get_and_patch(db_session, client_factory, user_factory):
    _make_user(db_session, user_factory, "employee@example.test", UserRole.EMPLOYEE)
    login_as(client_factory, "employee@example.test", "pass123456")
    r = client_factory.get("/settings/organization")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"
    r2 = client_factory.patch(
        "/settings/organization", json={"retention_days": 120}
    )
    assert r2.status_code == 403
    assert r2.json()["error"]["code"] == "forbidden"


def test_check_order_401_403_csrf_422(db_session, client_factory, user_factory, organization):
    """Guards run in strict order: 401, then RBAC 403, then CSRF 403, then 422."""
    # 401: no session at all
    r401 = client_factory.patch(
        "/api/v1/settings/organization",
        json={"retention_days": 0},
    )
    assert r401.status_code == 401
    assert r401.json()["error"]["code"] == "unauthenticated"

    # 403 RBAC: authenticated non-admin with an invalid body still gets 403,
    # not 422 and not 403 csrf_failed
    _make_user(db_session, user_factory, "order-analyst@example.test", UserRole.ANALYST)
    login_as(client_factory, "order-analyst@example.test", "pass123456")
    r403 = client_factory.patch(
        "/api/v1/settings/organization",
        json={"retention_days": 0},
    )
    assert r403.status_code == 403
    assert r403.json()["error"]["code"] == "forbidden"

    # 403 CSRF: admin without a CSRF token gets csrf_failed, not 422
    _make_user(db_session, user_factory, "order-admin@example.test", UserRole.ADMIN)
    login_as(client_factory, "order-admin@example.test", "pass123456")
    r_csrf = client_factory.patch(
        "/api/v1/settings/organization",
        json={"retention_days": 0},
    )
    assert r_csrf.status_code == 403
    assert r_csrf.json()["error"]["code"] == "csrf_failed"

    # 422: admin with valid CSRF token but invalid retention_days
    token = session_csrf_token(client_factory)
    r422 = client_factory.patch(
        "/api/v1/settings/organization",
        json={"retention_days": 0},
        headers={"X-CSRF-Token": token},
    )
    assert r422.status_code == 422
    assert r422.json()["error"]["code"] == "validation_error"
    assert "retention_days" in r422.json()["error"]["fields"]


def test_admin_get_returns_defaults(db_session, client_factory, user_factory, organization):
    _make_user(db_session, user_factory, "settings-admin@example.test", UserRole.ADMIN)
    login_as(client_factory, "settings-admin@example.test", "pass123456")
    r = client_factory.get("/api/v1/settings/organization")
    assert r.status_code == 200
    s = r.json()["settings"]
    assert s["retention_days"] == 90
    assert s["min_group_size"] == 5
    assert s["timezone"] == "UTC"
    assert s["send_domain_allowlist"] == ["example.com", "*.test", "*.invalid"]
    assert s["name"] == "Test Organization"


def test_admin_patch_updates_all_fields(db_session, client_factory, user_factory, organization):
    _make_user(db_session, user_factory, "patch-admin@example.test", UserRole.ADMIN)
    login_as(client_factory, "patch-admin@example.test", "pass123456")
    token = session_csrf_token(client_factory)
    r = client_factory.patch(
        "/api/v1/settings/organization",
        json={
            "name": "Acme Security",
            "primary_domain": "acme.test",
            "timezone": "Europe/Berlin",
            "retention_days": 120,
            "min_group_size": 10,
            "send_domain_allowlist": ["example.com"],
        },
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 200, r.text
    s = r.json()["settings"]
    assert s == {
        "name": "Acme Security",
        "primary_domain": "acme.test",
        "timezone": "Europe/Berlin",
        "retention_days": 120,
        "min_group_size": 10,
        "send_domain_allowlist": ["example.com"],
    }
    db_session.expire_all()
    org = organization
    assert org.retention_days == 120
    assert org.timezone == "Europe/Berlin"


@pytest.mark.parametrize("bad", [0, -1, 366, 1000])
def test_retention_days_out_of_bounds_422(db_session, client_factory, user_factory, bad):
    _make_user(db_session, user_factory, f"ret-admin-{bad}@example.test", UserRole.ADMIN)
    login_as(client_factory, f"ret-admin-{bad}@example.test", "pass123456")
    token = session_csrf_token(client_factory)
    r = client_factory.patch(
        "/api/v1/settings/organization",
        json={"retention_days": bad},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 422
    assert "retention_days" in r.json()["error"]["fields"]


@pytest.mark.parametrize("good", [1, 365])
def test_retention_days_at_bounds_ok(db_session, client_factory, user_factory, good):
    _make_user(db_session, user_factory, f"ret-ok-admin-{good}@example.test", UserRole.ADMIN)
    login_as(client_factory, f"ret-ok-admin-{good}@example.test", "pass123456")
    token = session_csrf_token(client_factory)
    r = client_factory.patch(
        "/api/v1/settings/organization",
        json={"retention_days": good},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 200, r.text
    assert r.json()["settings"]["retention_days"] == good


def test_timezone_invalid_422(db_session, client_factory, user_factory):
    _make_user(db_session, user_factory, "tz-admin@example.test", UserRole.ADMIN)
    login_as(client_factory, "tz-admin@example.test", "pass123456")
    token = session_csrf_token(client_factory)
    r = client_factory.patch(
        "/api/v1/settings/organization",
        json={"timezone": "Mars/Olympus"},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 422
    fields = r.json()["error"]["fields"]
    assert "timezone" in fields


def test_timezone_valid_names_accepted(db_session, client_factory, user_factory):
    _make_user(db_session, user_factory, "tz-ok-admin@example.test", UserRole.ADMIN)
    login_as(client_factory, "tz-ok-admin@example.test", "pass123456")
    token = session_csrf_token(client_factory)
    for tz in ["UTC", "Europe/Berlin", "Asia/Karachi", "America/New_York"]:
        r = client_factory.patch(
            "/api/v1/settings/organization",
            json={"timezone": tz},
            headers={"X-CSRF-Token": token},
        )
        assert r.status_code == 200, r.text
        assert r.json()["settings"]["timezone"] == tz


def test_blank_name_422(db_session, client_factory, user_factory):
    _make_user(db_session, user_factory, "name-admin@example.test", UserRole.ADMIN)
    login_as(client_factory, "name-admin@example.test", "pass123456")
    token = session_csrf_token(client_factory)
    r = client_factory.patch(
        "/api/v1/settings/organization",
        json={"name": "   "},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 422
    assert "name" in r.json()["error"]["fields"]


@pytest.mark.parametrize(
    "bad_domain", ["https://acme.test", "acme", "acme..test", "-bad.test", "acme.test/path"]
)
def test_invalid_primary_domain_422(db_session, client_factory, user_factory, bad_domain):
    _make_user(db_session, user_factory, f"dom-admin-{abs(hash(bad_domain))}@example.test", UserRole.ADMIN)
    login_as(client_factory, f"dom-admin-{abs(hash(bad_domain))}@example.test", "pass123456")
    token = session_csrf_token(client_factory)
    r = client_factory.patch(
        "/api/v1/settings/organization",
        json={"primary_domain": bad_domain},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 422, r.text
    assert "primary_domain" in r.json()["error"]["fields"]


def test_db_check_rejects_retention_days_out_of_bounds(db_session, organization):
    """Direct SQL outside 1..365 must be rejected by the CHECK constraint."""
    db_session.commit()
    with pytest.raises(IntegrityError):
        db_session.execute(
            text("UPDATE organizations SET retention_days = 0 WHERE id = :id"),
            {"id": organization.id},
        )
    db_session.rollback()
    with pytest.raises(IntegrityError):
        db_session.execute(
            text("UPDATE organizations SET retention_days = 366 WHERE id = :id"),
            {"id": organization.id},
        )
    db_session.rollback()
    db_session.execute(
        text("UPDATE organizations SET retention_days = 1 WHERE id = :id"),
        {"id": organization.id},
    )
    db_session.execute(
        text("UPDATE organizations SET retention_days = 365 WHERE id = :id"),
        {"id": organization.id},
    )
