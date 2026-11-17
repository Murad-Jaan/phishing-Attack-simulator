"""Idempotent campaign delivery for the Celery beat dispatcher.

Every target receives at most one row in ``campaign_sends``. The dispatcher
re-checks the authorization, scope, send window and rate cap at send time so a
pause, cancellation, scope change or expiry always wins over a stale schedule.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import mail
from app.core.audit import write_audit
from app.models.campaign import (
    Authorization,
    AuthorizationStatus,
    Campaign,
    CampaignSend,
    CampaignSendStatus,
    CampaignStatus,
)
from app.models.group import GroupMember
from app.models.organization import Organization
from app.models.target import Target
from app.models.template import Template
from app.models.tracking import TrackingLink
from app.services import campaign_service, tracking_service


def utcnow() -> datetime:
    return datetime.now(UTC)


def ensure_send_rows(db: Session, campaign: Campaign) -> int:
    """Create missing per-target rows without duplicating existing rows."""
    if campaign.group_id is None or campaign.send_time is None:
        return 0
    existing = set(
        db.execute(
            select(CampaignSend.target_id).where(
                CampaignSend.campaign_id == campaign.id
            )
        ).scalars()
    )
    targets = list(
        db.execute(
            select(Target.id)
            .join(GroupMember, GroupMember.target_id == Target.id)
            .where(GroupMember.group_id == campaign.group_id)
            .order_by(Target.email.asc(), Target.id.asc())
        ).scalars()
    )
    send_time = campaign_service.ensure_utc(campaign.send_time)
    rate_cap = campaign_service.effective_rate_cap(campaign)
    created = 0
    for index, target_id in enumerate(targets):
        if target_id in existing:
            continue
        db.add(
            CampaignSend(
                org_id=campaign.org_id,
                campaign_id=campaign.id,
                target_id=target_id,
                scheduled_for=send_time
                + timedelta(hours=index // max(rate_cap, 1)),
                status=CampaignSendStatus.QUEUED.value,
            )
        )
        created += 1
    if created:
        db.flush()
    return created


def _audit(
    db: Session,
    campaign: Campaign,
    action: str,
    *,
    after: dict[str, Any],
    reason: str | None = None,
) -> None:
    write_audit(
        db,
        org_id=campaign.org_id,
        actor_user_id=None,
        action=action,
        entity_type="campaign",
        entity_id=str(campaign.id),
        after=after,
        reason=reason or "system",
    )


def _block(
    db: Session,
    campaign: Campaign,
    reason_code: str,
    *,
    auth: Authorization | None = None,
) -> None:
    campaign.status = CampaignStatus.PAUSED
    db.add(campaign)
    if auth is not None and campaign_service.effective_status(auth) == AuthorizationStatus.EXPIRED:
        auth.status = AuthorizationStatus.EXPIRED
        db.add(auth)
    _audit(
        db,
        campaign,
        "campaign.send_blocked",
        after={"reason": reason_code},
        reason="system",
    )
    db.flush()


def _skip_remaining(db: Session, campaign: Campaign, now: datetime) -> int:
    rows = list(
        db.execute(
            select(CampaignSend).where(
                CampaignSend.campaign_id == campaign.id,
                CampaignSend.status == CampaignSendStatus.QUEUED.value,
            )
        ).scalars()
    )
    for row in rows:
        row.status = CampaignSendStatus.SKIPPED.value
        row.failure_code = "send_window_closed"
        db.add(row)
    if rows:
        db.flush()
    return len(rows)


def dispatch_campaign(
    db: Session,
    campaign: Campaign,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Deliver one rate-limited batch for a single campaign."""
    reference = now or utcnow()
    org = db.get(Organization, campaign.org_id)
    if org is None:
        return {"campaign_id": str(campaign.id), "sent": 0, "status": "missing_org"}

    auth = campaign_service.latest_authorization(db, campaign.id)
    if auth is None or auth.status != AuthorizationStatus.APPROVED:
        _block(db, campaign, "authorization_missing", auth=auth)
        return {"campaign_id": str(campaign.id), "sent": 0, "status": "blocked"}

    if (
        campaign_service.effective_status(auth, reference)
        == AuthorizationStatus.EXPIRED
        or campaign_service.ensure_utc(auth.end_date) < reference
    ):
        _block(db, campaign, "authorization_expired", auth=auth)
        return {"campaign_id": str(campaign.id), "sent": 0, "status": "expired"}

    problems = campaign_service.scope_mismatches(db, campaign, auth)
    if problems:
        _audit(
            db,
            campaign,
            "campaign.send_blocked",
            after={"reason": "scope_changed", "fields": sorted(problems)},
            reason="system",
        )
        campaign.status = CampaignStatus.PAUSED
        db.add(campaign)
        db.flush()
        return {"campaign_id": str(campaign.id), "sent": 0, "status": "scope_changed"}

    if campaign.status not in (CampaignStatus.SCHEDULED, CampaignStatus.RUNNING):
        return {
            "campaign_id": str(campaign.id),
            "sent": 0,
            "status": campaign.status.value,
        }

    window_start, window_end = campaign_service.effective_window(campaign)
    if reference < window_start:
        return {"campaign_id": str(campaign.id), "sent": 0, "status": "waiting"}
    if reference > window_end:
        skipped = _skip_remaining(db, campaign, reference)
        _block(db, campaign, "send_window_closed")
        return {
            "campaign_id": str(campaign.id),
            "sent": 0,
            "skipped": skipped,
            "status": "window_closed",
        }

    template = db.get(Template, campaign.template_id) if campaign.template_id else None
    if template is None or template.org_id != campaign.org_id:
        _block(db, campaign, "template_missing")
        return {"campaign_id": str(campaign.id), "sent": 0, "status": "blocked"}

    ensure_send_rows(db, campaign)
    tracking_service.ensure_tracking_links(db, campaign)
    links = {
        link.target_id: link
        for link in db.execute(
            select(TrackingLink).where(TrackingLink.campaign_id == campaign.id)
        ).scalars()
    }

    rate_cap = campaign_service.effective_rate_cap(campaign)
    sent_last_hour = int(
        db.execute(
            select(func.count(CampaignSend.id)).where(
                CampaignSend.campaign_id == campaign.id,
                CampaignSend.status == CampaignSendStatus.SENT.value,
                CampaignSend.sent_at >= reference - timedelta(hours=1),
            )
        ).scalar_one()
    )
    allowance = max(0, rate_cap - sent_last_hour)
    if allowance == 0:
        return {"campaign_id": str(campaign.id), "sent": 0, "status": "rate_limited"}

    rows = list(
        db.execute(
            select(CampaignSend)
            .where(
                CampaignSend.campaign_id == campaign.id,
                CampaignSend.status == CampaignSendStatus.QUEUED.value,
                CampaignSend.scheduled_for <= reference,
            )
            .order_by(CampaignSend.scheduled_for.asc(), CampaignSend.id.asc())
            .limit(allowance)
            .with_for_update(skip_locked=True)
        ).scalars()
    )

    sent = 0
    failed = 0
    for row in rows:
        target = db.get(Target, row.target_id)
        if target is None:
            row.status = CampaignSendStatus.SKIPPED.value
            row.failure_code = "target_missing"
            db.add(row)
            continue
        link = links.get(target.id)
        if link is None:
            row.status = CampaignSendStatus.FAILED.value
            row.failure_code = "tracking_missing"
            failed += 1
            db.add(row)
            continue
        first_name = (target.display_name or "there").split()[0]
        tracking_link = tracking_service.tracking_url(campaign, link.token)
        subject = campaign_service._fill_placeholders(
            template.subject, first_name, tracking_link
        )
        body = campaign_service._fill_placeholders(
            template.body, first_name, tracking_link
        )
        html_body = mail.body_to_html(body, tracking_link)
        try:
            mail.send_mail_sandbox(
                target.email, subject, body, html_body=html_body
            )
        except Exception:
            row.status = CampaignSendStatus.FAILED.value
            row.failure_code = "delivery_failed"
            failed += 1
        else:
            row.status = CampaignSendStatus.SENT.value
            row.sent_at = reference
            tracking_service.record_delivered(db, link)
            sent += 1
        db.add(row)

    db.flush()
    remaining = int(
        db.execute(
            select(func.count(CampaignSend.id)).where(
                CampaignSend.campaign_id == campaign.id,
                CampaignSend.status == CampaignSendStatus.QUEUED.value,
            )
        ).scalar_one()
    )
    campaign.status = (
        CampaignStatus.COMPLETED if remaining == 0 else CampaignStatus.RUNNING
    )
    db.add(campaign)
    if sent or failed or remaining == 0:
        _audit(
            db,
            campaign,
            "campaign.send_batch",
            after={"sent": sent, "failed": failed, "remaining": remaining},
            reason="system",
        )
    db.flush()
    return {
        "campaign_id": str(campaign.id),
        "sent": sent,
        "failed": failed,
        "remaining": remaining,
        "status": campaign.status.value,
    }


def dispatch_due(
    db: Session,
    *,
    now: datetime | None = None,
    campaign_id: uuid.UUID | None = None,
    org_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Dispatch every due campaign, scoped optionally to one campaign or org."""
    reference = now or utcnow()
    stmt = select(Campaign).where(
        Campaign.status.in_([CampaignStatus.SCHEDULED, CampaignStatus.RUNNING])
    )
    if campaign_id is not None:
        stmt = stmt.where(Campaign.id == campaign_id)
    if org_id is not None:
        stmt = stmt.where(Campaign.org_id == org_id)
    campaigns = list(
        db.execute(stmt.order_by(Campaign.send_time.asc(), Campaign.id.asc())).scalars()
    )
    results = [
        dispatch_campaign(db, campaign, now=reference) for campaign in campaigns
    ]
    return {
        "campaigns": len(campaigns),
        "sent": sum(item.get("sent", 0) for item in results),
        "results": results,
    }
