"""M2 organization settings audit: changed fields only, no secrets, no-op no row."""

from sqlalchemy import func, select

from app.core.security import hash_password
from app.models import AuditLog
from app.models.user import UserRole
from tests.conftest import login_as, session_csrf_token

SETTINGS_URL = "/api/v1/settings/organization"


def _login_admin(db_session, client_factory, user_factory, email: str) -> str:
    user = user_factory(email=email, role=UserRole.ADMIN)
    user.password_hash = hash_password("pass123456")
    db_session.commit()
    login_as(client_factory, email, "pass123456")
    return session_csrf_token(client_factory)


def _settings_audit_count(db_session, organization) -> int:
    return db_session.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.action == "org_settings.update",
            AuditLog.org_id == organization.id,
        )
    ).scalar_one()


def test_noop_patch_writes_no_audit_row(db_session, client_factory, user_factory, organization):
    token = _login_admin(db_session, client_factory, user_factory, "audit-noop@example.test")
    before = _settings_audit_count(db_session, organization)
    r = client_factory.patch(
        SETTINGS_URL,
        json={"retention_days": 90, "min_group_size": 5, "timezone": "UTC"},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 200, r.text
    db_session.expire_all()
    assert _settings_audit_count(db_session, organization) == before


def test_single_change_audits_only_changed_field(
    db_session, client_factory, user_factory, organization
):
    token = _login_admin(db_session, client_factory, user_factory, "audit-one@example.test")
    r = client_factory.patch(
        SETTINGS_URL,
        json={"retention_days": 120},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 200, r.text
    db_session.expire_all()
    row = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.action == "org_settings.update",
            AuditLog.org_id == organization.id,
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.before == {"retention_days": 90}
    assert row.after == {"retention_days": 120}
    assert row.entity_type == "organization"
    assert row.entity_id == str(organization.id)
    assert row.actor_user_id is not None


def test_multi_change_audits_only_changed_fields(
    db_session, client_factory, user_factory, organization
):
    token = _login_admin(db_session, client_factory, user_factory, "audit-multi@example.test")
    r = client_factory.patch(
        SETTINGS_URL,
        json={"timezone": "Europe/Berlin", "min_group_size": 12},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 200, r.text
    db_session.expire_all()
    row = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.action == "org_settings.update",
            AuditLog.org_id == organization.id,
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert row is not None
    assert set(row.before) == {"timezone", "min_group_size"}
    assert set(row.after) == {"timezone", "min_group_size"}
    assert row.before["min_group_size"] == 5
    assert row.after["min_group_size"] == 12
    assert row.after["timezone"] == "Europe/Berlin"


def test_audit_payload_keys_are_setting_fields_only(
    db_session, client_factory, user_factory, organization
):
    """No secrets: payload keys must be a subset of the settings field names."""
    token = _login_admin(db_session, client_factory, user_factory, "audit-keys@example.test")
    r = client_factory.patch(
        SETTINGS_URL,
        json={"name": "Renamed Org", "send_domain_allowlist": ["example.com"]},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 200, r.text
    db_session.expire_all()
    row = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.action == "org_settings.update",
            AuditLog.org_id == organization.id,
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert row is not None
    allowed = {
        "name",
        "primary_domain",
        "timezone",
        "retention_days",
        "min_group_size",
        "send_domain_allowlist",
    }
    assert set(row.before) <= allowed
    assert set(row.after) <= allowed
    assert row.before["send_domain_allowlist"] == ["example.com", "*.test", "*.invalid"]
    assert row.after["send_domain_allowlist"] == ["example.com"]
