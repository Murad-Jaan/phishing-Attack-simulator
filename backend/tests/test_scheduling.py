"""M6 scheduling: beat dispatch, send windows, rate caps and audit export."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.api.v1.audit import _csv_cell
from app.models import (
    AuditLog,
    Authorization,
    Campaign,
    CampaignSend,
    CampaignSendStatus,
    CampaignStatus,
)
from app.services import scheduling_service
from tests.conftest import login_as
from tests.test_campaigns import PASSWORD, _approved_campaign, _csrf, _setup


def _campaign(db_session, campaign_id: str) -> Campaign:
    db_session.expire_all()
    campaign = db_session.get(Campaign, campaign_id)
    assert campaign is not None
    return campaign


def _sends(db_session, campaign_id: str) -> list[CampaignSend]:
    db_session.expire_all()
    return list(
        db_session.execute(
            select(CampaignSend)
            .where(CampaignSend.campaign_id == campaign_id)
            .order_by(CampaignSend.scheduled_for, CampaignSend.id)
        ).scalars()
    )


def test_schedule_endpoint_activates_approved_campaign(
    db_session, client_factory, organization
):
    setup = _setup(db_session, organization)
    campaign_id, _auth_id = _approved_campaign(db_session, client_factory, organization, setup)
    login_as(client_factory, setup[0].email, PASSWORD)

    response = client_factory.post(
        f"/api/v1/campaigns/{campaign_id}/schedule", json={}, headers=_csrf(client_factory)
    )

    assert response.status_code == 200, response.text
    assert response.json()["campaign"]["status"] == "scheduled"
    campaign = _campaign(db_session, campaign_id)
    assert campaign.status == CampaignStatus.SCHEDULED


def test_dispatch_waits_then_delivers_once_and_completes(
    db_session, client_factory, organization
):
    setup = _setup(db_session, organization)
    campaign_id, _auth_id = _approved_campaign(db_session, client_factory, organization, setup)
    login_as(client_factory, setup[0].email, PASSWORD)
    client_factory.post(
        f"/api/v1/campaigns/{campaign_id}/schedule", json={}, headers=_csrf(client_factory)
    )
    campaign = _campaign(db_session, campaign_id)
    send_time = campaign.send_time
    assert send_time is not None

    early = scheduling_service.dispatch_due(
        db_session, now=send_time - timedelta(minutes=1)
    )
    assert early["campaigns"] == 1
    assert early["sent"] == 0
    assert _campaign(db_session, campaign_id).status == CampaignStatus.SCHEDULED

    on_time = scheduling_service.dispatch_due(db_session, now=send_time)
    assert on_time["sent"] == 5
    db_session.commit()

    rows = _sends(db_session, campaign_id)
    assert len(rows) == 5
    assert {row.status for row in rows} == {CampaignSendStatus.SENT.value}
    assert _campaign(db_session, campaign_id).status == CampaignStatus.COMPLETED

    again = scheduling_service.dispatch_due(db_session, now=send_time + timedelta(hours=1))
    assert again["sent"] == 0
    assert len(_sends(db_session, campaign_id)) == 5


def test_rate_cap_limits_each_batch_and_closed_window_skips(
    db_session, client_factory, organization
):
    setup = _setup(db_session, organization)
    campaign_id, auth_id = _approved_campaign(
        db_session, client_factory, organization, setup
    )
    login_as(client_factory, setup[0].email, PASSWORD)
    campaign = _campaign(db_session, campaign_id)
    campaign.rate_cap_per_hour = 2
    auth = db_session.get(Authorization, auth_id)
    assert auth is not None
    auth.rate_cap_per_hour = 2
    assert campaign.send_time is not None
    campaign.send_window_end = campaign.send_time + timedelta(hours=1)
    auth.send_window_end = campaign.send_window_end
    db_session.commit()
    client_factory.post(
        f"/api/v1/campaigns/{campaign_id}/schedule", json={}, headers=_csrf(client_factory)
    )
    campaign = _campaign(db_session, campaign_id)
    send_time = campaign.send_time

    first = scheduling_service.dispatch_due(db_session, now=send_time)
    assert first["sent"] == 2
    db_session.commit()
    second = scheduling_service.dispatch_due(
        db_session, now=send_time + timedelta(minutes=10)
    )
    assert second["sent"] == 0
    assert _campaign(db_session, campaign_id).status == CampaignStatus.RUNNING

    _, window_end = campaign.send_window_start, campaign.send_window_end
    assert window_end is not None
    closed = scheduling_service.dispatch_due(
        db_session, now=window_end + timedelta(hours=1)
    )
    assert closed["campaigns"] == 1
    db_session.commit()
    skipped = [row for row in _sends(db_session, campaign_id) if row.status == "skipped"]
    assert skipped
    assert _campaign(db_session, campaign_id).status == CampaignStatus.PAUSED


def test_expired_authorization_blocks_at_send_time(
    db_session, client_factory, organization
):
    setup = _setup(db_session, organization)
    campaign_id, auth_id = _approved_campaign(
        db_session, client_factory, organization, setup
    )
    login_as(client_factory, setup[0].email, PASSWORD)
    client_factory.post(
        f"/api/v1/campaigns/{campaign_id}/schedule", json={}, headers=_csrf(client_factory)
    )
    auth = db_session.get(Authorization, auth_id)
    assert auth is not None
    auth.end_date = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    result = scheduling_service.dispatch_due(
        db_session, now=datetime.now(UTC)
    )

    assert result["sent"] == 0
    db_session.commit()
    assert _campaign(db_session, campaign_id).status == CampaignStatus.PAUSED
    assert _sends(db_session, campaign_id) == []
    row = db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "campaign.send_blocked",
            AuditLog.entity_id == campaign_id,
        )
    ).scalars().first()
    assert row is not None
    assert row.after == {"reason": "authorization_expired"}


def test_audit_list_and_csv_export_are_admin_only_with_csrf(
    db_session, client_factory, organization
):
    setup = _setup(db_session, organization)
    campaign_id, _auth_id = _approved_campaign(
        db_session, client_factory, organization, setup
    )
    login_as(client_factory, setup[0].email, PASSWORD)

    listing = client_factory.get("/api/v1/audit?action=campaign.&limit=10")
    assert listing.status_code == 200, listing.text
    body = listing.json()
    assert body["total"] >= 1
    assert all(event["action"].startswith("campaign.") for event in body["events"])
    assert any(event["entity_id"] == campaign_id for event in body["events"])

    no_csrf = client_factory.post("/api/v1/audit/export", json={})
    assert no_csrf.status_code == 403

    export = client_factory.post(
        "/api/v1/audit/export", json={"entity_id": campaign_id}, headers=_csrf(client_factory)
    )
    assert export.status_code == 200, export.text
    assert export.headers["content-type"].startswith("text/csv")
    assert "attachment" in export.headers["content-disposition"]
    assert "created_at,action,entity_type" in export.text
    assert campaign_id in export.text
    assert "password" not in export.text.lower()

    db_session.expire_all()
    audit_export = db_session.execute(
        select(AuditLog).where(AuditLog.action == "audit.export")
    ).scalars().first()
    assert audit_export is not None
    assert audit_export.actor_user_id == setup[0].id


@pytest.mark.parametrize("value", ["=1+1", "+CMD", "-2+3", "@SUM(A1)", "\t=evil"])
def test_csv_export_neutralizes_formula_cells(value):
    assert _csv_cell(value).startswith("'")


def test_csv_export_flattens_newlines_and_keeps_json():
    assert _csv_cell("a\nb\r\nc") == "a b  c"
    assert _csv_cell({"ok": True}) == '{"ok": true}'


def test_pause_then_resume_keeps_schedule(db_session, client_factory, organization):
    setup = _setup(db_session, organization)
    campaign_id, _auth_id = _approved_campaign(
        db_session, client_factory, organization, setup
    )
    login_as(client_factory, setup[0].email, PASSWORD)
    client_factory.post(
        f"/api/v1/campaigns/{campaign_id}/schedule", json={}, headers=_csrf(client_factory)
    )

    paused = client_factory.post(
        f"/api/v1/campaigns/{campaign_id}/pause", json={}, headers=_csrf(client_factory)
    )
    assert paused.status_code == 200, paused.text
    assert paused.json()["campaign"]["status"] == "paused"

    resumed = client_factory.post(
        f"/api/v1/campaigns/{campaign_id}/resume", json={}, headers=_csrf(client_factory)
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["campaign"]["status"] in {"scheduled", "running"}


def test_cancel_marks_remaining_sends_cancelled(
    db_session, client_factory, organization
):
    setup = _setup(db_session, organization)
    campaign_id, _auth_id = _approved_campaign(
        db_session, client_factory, organization, setup
    )
    login_as(client_factory, setup[0].email, PASSWORD)
    campaign = _campaign(db_session, campaign_id)
    campaign.rate_cap_per_hour = 2
    auth = db_session.get(Authorization, _auth_id)
    assert auth is not None
    auth.rate_cap_per_hour = 2
    db_session.commit()
    client_factory.post(
        f"/api/v1/campaigns/{campaign_id}/schedule", json={}, headers=_csrf(client_factory)
    )
    campaign = _campaign(db_session, campaign_id)
    scheduling_service.dispatch_due(db_session, now=campaign.send_time)
    db_session.commit()

    cancelled = client_factory.post(
        f"/api/v1/campaigns/{campaign_id}/cancel", json={}, headers=_csrf(client_factory)
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["campaign"]["status"] == "cancelled"

    rows = _sends(db_session, campaign_id)
    assert any(row.status == CampaignSendStatus.SENT.value for row in rows)
    assert all(
        row.status in {CampaignSendStatus.SENT.value, CampaignSendStatus.CANCELLED.value}
        for row in rows
    )
    assert any(row.status == CampaignSendStatus.CANCELLED.value for row in rows)


def test_scope_rate_change_blocks_dispatch(db_session, client_factory, organization):
    setup = _setup(db_session, organization)
    campaign_id, _auth_id = _approved_campaign(
        db_session, client_factory, organization, setup
    )
    login_as(client_factory, setup[0].email, PASSWORD)
    client_factory.post(
        f"/api/v1/campaigns/{campaign_id}/schedule", json={}, headers=_csrf(client_factory)
    )
    campaign = _campaign(db_session, campaign_id)
    campaign.rate_cap_per_hour = 10
    db_session.commit()

    result = scheduling_service.dispatch_due(
        db_session, now=campaign.send_time
    )

    assert result["sent"] == 0
    db_session.commit()
    assert _campaign(db_session, campaign_id).status == CampaignStatus.PAUSED
    row = db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "campaign.send_blocked",
            AuditLog.entity_id == campaign_id,
        )
    ).scalars().first()
    assert row is not None
    assert row.after["reason"] == "scope_changed"
    assert "rate_cap_per_hour" in row.after["fields"]
