"""M2 retention preview and Celery task behaviour."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    AuditLog,
    AuthSession,
    Campaign,
    CampaignSend,
    CampaignSendStatus,
    CampaignStatus,
    Organization,
    Target,
    User,
    UserRole,
)
from app.services import session_service
from app.worker import tasks
from tests.conftest import login_as

PREVIEW_URL = "/api/v1/settings/retention/preview"


def _make_user(db_session, user_factory, email: str, role: UserRole) -> User:
    user = user_factory(email=email, role=role)
    user.password_hash = hash_password("pass123456")
    db_session.commit()
    return user


def _make_session(
    db_session,
    user: User,
    *,
    expires_at: datetime | None = None,
    revoked_at: datetime | None = None,
) -> AuthSession:
    sess, _ = session_service.create_session(db_session, user)
    if expires_at is not None:
        sess.expires_at = expires_at
    if revoked_at is not None:
        sess.revoked_at = revoked_at
    db_session.add(sess)
    db_session.commit()
    return sess


def _session_count(db_session) -> int:
    return int(db_session.execute(select(func.count(AuthSession.id))).scalar_one())


def _retention_audit_rows(db_session) -> list[AuditLog]:
    return list(
        db_session.execute(
            select(AuditLog)
            .where(AuditLog.action == "retention.run")
            .order_by(AuditLog.id)
        )
        .scalars()
        .all()
    )


def _patch_task_session(monkeypatch, db_session) -> None:
    connection = db_session.get_bind()

    def factory() -> Session:
        return Session(bind=connection, join_transaction_mode="create_savepoint")

    monkeypatch.setattr(tasks, "SessionLocal", factory)


def _seed_old_and_recent_sessions(db_session, user_factory):
    now = datetime.now(timezone.utc)
    admin = _make_user(db_session, user_factory, "retention-admin@example.test", UserRole.ADMIN)
    target = _make_user(db_session, user_factory, "retention-target@example.test", UserRole.EMPLOYEE)

    old_expired = _make_session(
        db_session, target, expires_at=now - timedelta(days=8)
    )
    old_revoked = _make_session(
        db_session,
        target,
        expires_at=now + timedelta(days=1),
        revoked_at=now - timedelta(days=8),
    )
    recent_expired = _make_session(
        db_session, target, expires_at=now - timedelta(days=1)
    )
    recent_revoked = _make_session(
        db_session,
        target,
        expires_at=now + timedelta(days=1),
        revoked_at=now - timedelta(days=1),
    )
    active = _make_session(db_session, target, expires_at=now + timedelta(days=1))
    return admin, old_expired, old_revoked, recent_expired, recent_revoked, active


def _seed_other_org_old_session(db_session) -> AuthSession:
    now = datetime.now(timezone.utc)
    other_org = Organization(
        name="Other Organization",
        slug="other-retention-org",
        primary_domain="other.test",
        is_demo=False,
    )
    db_session.add(other_org)
    db_session.flush()
    other_user = User(
        org_id=other_org.id,
        email="other-retention-user@example.test",
        password_hash="not-a-real-hash",
        display_name="Other User",
        role=UserRole.EMPLOYEE,
    )
    db_session.add(other_user)
    db_session.flush()
    return _make_session(
        db_session, other_user, expires_at=now - timedelta(days=8)
    )


def test_preview_counts_only_old_sessions_for_admin_org_and_deletes_nothing(
    db_session, client_factory, user_factory, organization
):
    admin, old_expired, old_revoked, *_ = _seed_old_and_recent_sessions(
        db_session, user_factory
    )
    _seed_other_org_old_session(db_session)
    login_as(client_factory, admin.email, "pass123456")

    before = _session_count(db_session)
    audit_before = len(_retention_audit_rows(db_session))
    response = client_factory.get(PREVIEW_URL)

    assert response.status_code == 200, response.text
    assert response.json() == {"scopes": {"sessions": 2, "campaign_sends": 0}}
    assert _session_count(db_session) == before
    assert len(_retention_audit_rows(db_session)) == audit_before
    assert db_session.get(AuthSession, old_expired.id) is not None
    assert db_session.get(AuthSession, old_revoked.id) is not None
    assert organization.id is not None


def test_preview_response_contains_no_tokens_or_hashes(
    db_session, client_factory, user_factory
):
    admin, *_ = _seed_old_and_recent_sessions(db_session, user_factory)
    login_as(client_factory, admin.email, "pass123456")

    response = client_factory.get(PREVIEW_URL)

    assert response.status_code == 200, response.text
    text = response.text.lower()
    assert "token" not in text
    assert "hash" not in text
    assert "csrf" not in text
    assert "revoked" not in text
    assert set(response.json()) == {"scopes"}


def test_preview_unauthenticated_401(client_factory):
    response = client_factory.get(PREVIEW_URL)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


@pytest.mark.parametrize("role", [UserRole.ANALYST, UserRole.EMPLOYEE])
def test_preview_non_admin_403(db_session, client_factory, user_factory, role):
    user = _make_user(
        db_session, user_factory, f"retention-{role.value}@example.test", role
    )
    login_as(client_factory, user.email, "pass123456")

    response = client_factory.get(PREVIEW_URL)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_dry_run_task_deletes_nothing_and_writes_no_audit(
    db_session, monkeypatch, user_factory, organization
):
    _admin, old_expired, old_revoked, *_ = _seed_old_and_recent_sessions(
        db_session, user_factory
    )
    _patch_task_session(monkeypatch, db_session)

    before = _session_count(db_session)
    audit_before = len(_retention_audit_rows(db_session))
    result = tasks.retention_run.run(dry_run=True, org_id=str(organization.id))

    assert result == {"dry_run": True, "counts": {"sessions": 2, "campaign_sends": 0}}
    assert _session_count(db_session) == before
    assert len(_retention_audit_rows(db_session)) == audit_before
    assert db_session.get(AuthSession, old_expired.id) is not None
    assert db_session.get(AuthSession, old_revoked.id) is not None


def test_forced_run_deletes_only_old_expired_or_revoked_sessions_and_audits_once(
    db_session, monkeypatch, user_factory, organization
):
    (
        _admin,
        old_expired,
        old_revoked,
        recent_expired,
        recent_revoked,
        active,
    ) = _seed_old_and_recent_sessions(db_session, user_factory)
    other_org_old = _seed_other_org_old_session(db_session)
    _patch_task_session(monkeypatch, db_session)
    old_expired_id = old_expired.id
    old_revoked_id = old_revoked.id
    recent_expired_id = recent_expired.id
    recent_revoked_id = recent_revoked.id
    active_id = active.id
    other_org_old_id = other_org_old.id

    result = tasks.retention_run.run(
        dry_run=False, force=True, org_id=str(organization.id)
    )

    assert result == {"dry_run": False, "counts": {"sessions": 2, "campaign_sends": 0}}
    db_session.expire_all()
    assert db_session.get(AuthSession, old_expired_id) is None
    assert db_session.get(AuthSession, old_revoked_id) is None
    assert db_session.get(AuthSession, recent_expired_id) is not None
    assert db_session.get(AuthSession, recent_revoked_id) is not None
    assert db_session.get(AuthSession, active_id) is not None
    assert db_session.get(AuthSession, other_org_old_id) is not None

    rows = _retention_audit_rows(db_session)
    assert len(rows) == 1
    row = rows[0]
    assert row.org_id == organization.id
    assert row.actor_user_id is None
    assert row.action == "retention.run"
    assert row.entity_type == "retention"
    assert row.before is None
    assert row.after == {"sessions": 2, "campaign_sends": 0}
    assert row.reason == "system"
    assert "token" not in str(row.after).lower()
    assert "hash" not in str(row.after).lower()


def test_second_forced_run_deletes_zero_and_writes_zero_count_audit(
    db_session, monkeypatch, user_factory, organization
):
    _seed_old_and_recent_sessions(db_session, user_factory)
    _patch_task_session(monkeypatch, db_session)

    first = tasks.retention_run.run(
        dry_run=False, force=True, org_id=str(organization.id)
    )
    assert first == {"dry_run": False, "counts": {"sessions": 2, "campaign_sends": 0}}
    assert len(_retention_audit_rows(db_session)) == 1

    second = tasks.retention_run.run(
        dry_run=False, force=True, org_id=str(organization.id)
    )

    assert second == {"dry_run": False, "counts": {"sessions": 0, "campaign_sends": 0}}
    rows = _retention_audit_rows(db_session)
    assert len(rows) == 2
    assert rows[1].after == {"sessions": 0, "campaign_sends": 0}
    assert rows[1].actor_user_id is None
    assert rows[1].reason == "system"


def test_task_refuses_destructive_run_without_force(monkeypatch):
    def fail_if_opened():
        raise AssertionError("task must refuse before opening a database session")

    monkeypatch.setattr(tasks, "SessionLocal", fail_if_opened)

    with pytest.raises(ValueError, match="force=True"):
        tasks.retention_run.run(dry_run=False)


def test_retention_deletes_only_old_campaign_sends(
    db_session, monkeypatch, user_factory, organization
):
    now = datetime.now(timezone.utc)
    target = Target(
        org_id=organization.id,
        email="retention-target-send@example.test",
        display_name="Send Target",
    )
    recent_target = Target(
        org_id=organization.id,
        email="retention-recent-send@example.test",
        display_name="Recent Send Target",
    )
    db_session.add_all([target, recent_target])
    campaign = Campaign(
        org_id=organization.id,
        name="Retention campaign",
        sending_domain="example.test",
        rate_cap_per_hour=60,
        status=CampaignStatus.COMPLETED,
        send_time=now - timedelta(days=400),
    )
    db_session.add(campaign)
    db_session.flush()
    old = CampaignSend(
        org_id=organization.id,
        campaign_id=campaign.id,
        target_id=target.id,
        scheduled_for=now - timedelta(days=400),
        status=CampaignSendStatus.SENT.value,
    )
    recent = CampaignSend(
        org_id=organization.id,
        campaign_id=campaign.id,
        target_id=recent_target.id,
        scheduled_for=now,
        status=CampaignSendStatus.QUEUED.value,
    )
    db_session.add_all([old, recent])
    db_session.flush()
    old_id, recent_id = old.id, recent.id
    db_session.execute(
        text(
            "UPDATE campaign_sends SET created_at = :created_at WHERE id = :id"
        ),
        {"created_at": now - timedelta(days=400), "id": old_id},
    )
    db_session.commit()
    _patch_task_session(monkeypatch, db_session)

    preview_counts = tasks.retention_run.run(dry_run=True, org_id=str(organization.id))
    assert preview_counts["counts"]["campaign_sends"] == 1

    result = tasks.retention_run.run(
        dry_run=False, force=True, org_id=str(organization.id)
    )
    assert result["counts"]["campaign_sends"] == 1
    db_session.expire_all()
    assert db_session.get(CampaignSend, old_id) is None
    assert db_session.get(CampaignSend, recent_id) is not None
