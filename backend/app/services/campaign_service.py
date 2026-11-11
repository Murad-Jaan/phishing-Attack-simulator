"""Campaign lifecycle, authorization gate and safe test sends.

The authorization gate is deliberately re-evaluated at launch instead of
trusting the campaign status. An approval captured a snapshot of the exact
scope an approver reviewed; any later change to the group, template version,
recipient count, sending domain or schedule invalidates that approval.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import mail
from app.core.config import settings
from app.models.campaign import (
    Authorization,
    AuthorizationStatus,
    Campaign,
    CampaignStatus,
)
from app.models.group import Group
from app.models.organization import Organization
from app.models.template import Template, TemplateStatus
from app.models.user import User
from app.services.groups_service import member_count

DEFAULT_TRACKING_LINK = "https://tracking.example.test/test/dummy"
TEST_SUBJECT_PREFIX = "[TEST] "
TEST_NOTICE = (
    "TEST MESSAGE - NOT A REAL PHISHING SIMULATION\n"
    "This message was sent only to a sandbox test inbox. No target "
    "recipients received it and no tracking data is collected.\n\n"
    "--- Simulation notice ---\n"
    "This is a phishing-awareness simulation test. If this were a real "
    "simulation, the recipient would receive safety guidance and a reporting "
    "channel. Never enter credentials in a simulated message.\n"
)
_PLACEHOLDER_RE = re.compile(r"\{\{\s*([^{}]*?)\s*\}\}")


class CampaignValidationError(Exception):
    def __init__(self, fields: dict[str, str]):
        super().__init__("campaign_validation_error")
        self.fields = fields


class CampaignConflictError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def utcnow() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def domain_allowed(org: Organization, domain: str) -> bool:
    value = (domain or "").strip().lower().rstrip(".")
    if not value:
        return False
    for pattern in org.send_domain_allowlist or []:
        entry = pattern.strip().lower()
        if entry.startswith("*."):
            suffix = entry[1:]
            if value.endswith(suffix) and value != entry[2:]:
                return True
        elif value == entry:
            return True
    return False


def target_count(db: Session, group_id: uuid.UUID | None) -> int:
    if group_id is None:
        return 0
    return member_count(db, group_id)


def latest_authorization(db: Session, campaign_id: uuid.UUID) -> Authorization | None:
    return db.execute(
        select(Authorization)
        .where(Authorization.campaign_id == campaign_id)
        .order_by(Authorization.created_at.desc(), Authorization.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def effective_status(auth: Authorization, now: datetime | None = None) -> AuthorizationStatus:
    if auth.status == AuthorizationStatus.APPROVED:
        when = now or utcnow()
        if ensure_utc(auth.end_date) < when:
            return AuthorizationStatus.EXPIRED
    return auth.status


def expire_stale(db: Session, org_id: uuid.UUID) -> int:
    now = utcnow()
    rows = list(
        db.execute(
            select(Authorization).where(
                Authorization.org_id == org_id,
                Authorization.status == AuthorizationStatus.APPROVED,
                Authorization.end_date < now,
            )
        ).scalars()
    )
    for row in rows:
        row.status = AuthorizationStatus.EXPIRED
        db.add(row)
    if rows:
        db.flush()
    return len(rows)


def serialize_authorization(db: Session, auth: Authorization) -> dict[str, Any]:
    requester = db.get(User, auth.requested_by) if auth.requested_by else None
    approver = db.get(User, auth.approved_by) if auth.approved_by else None
    campaign = db.get(Campaign, auth.campaign_id)
    group = db.get(Group, auth.group_id)
    template = db.get(Template, auth.template_id)
    return {
        "id": str(auth.id),
        "campaign_id": str(auth.campaign_id),
        "campaign_name": campaign.name if campaign else None,
        "campaign_status": campaign.status.value if campaign else None,
        "group_name": group.name if group else None,
        "template_name": template.name if template else None,
        "status": effective_status(auth).value,
        "reason": auth.reason,
        "requested_by": str(auth.requested_by) if auth.requested_by else None,
        "requested_by_email": requester.email if requester else None,
        "approved_by": str(auth.approved_by) if auth.approved_by else None,
        "approved_by_email": approver.email if approver else None,
        "group_id": str(auth.group_id),
        "template_id": str(auth.template_id),
        "template_version": auth.template_version,
        "target_count": auth.target_count,
        "sending_domain": auth.sending_domain,
        "scheduled_send_time": _iso(auth.scheduled_send_time),
        "start_date": _iso(auth.start_date),
        "end_date": _iso(auth.end_date),
        "requested_at": _iso(auth.created_at),
        "decided_at": _iso(auth.decided_at),
        "revoked_at": _iso(auth.revoked_at),
    }


def serialize_campaign(db: Session, campaign: Campaign) -> dict[str, Any]:
    group = db.get(Group, campaign.group_id) if campaign.group_id else None
    template = db.get(Template, campaign.template_id) if campaign.template_id else None
    creator = db.get(User, campaign.created_by) if campaign.created_by else None
    auth = latest_authorization(db, campaign.id)
    return {
        "id": str(campaign.id),
        "org_id": str(campaign.org_id),
        "name": campaign.name,
        "description": campaign.description,
        "template_id": str(campaign.template_id) if campaign.template_id else None,
        "template_version": campaign.template_version,
        "template_name": template.name if template else None,
        "group_id": str(campaign.group_id) if campaign.group_id else None,
        "group_name": group.name if group else None,
        "target_count": target_count(db, campaign.group_id),
        "send_time": _iso(campaign.send_time),
        "sending_domain": campaign.sending_domain,
        "status": campaign.status.value,
        "created_by": str(campaign.created_by) if campaign.created_by else None,
        "created_by_email": creator.email if creator else None,
        "authorization": serialize_authorization(db, auth) if auth else None,
        "created_at": _iso(campaign.created_at),
        "updated_at": _iso(campaign.updated_at),
    }


def _resolve_group(db: Session, org_id: uuid.UUID, group_id: uuid.UUID) -> Group:
    group = db.get(Group, group_id)
    if group is None or group.org_id != org_id:
        raise CampaignValidationError({"group_id": "Select a group in this organization."})
    return group


def _resolve_template(
    db: Session, org_id: uuid.UUID, template_id: uuid.UUID
) -> Template:
    template = db.get(Template, template_id)
    if template is None or template.org_id != org_id:
        raise CampaignValidationError(
            {"template_id": "Select a template in this organization."}
        )
    if template.status != TemplateStatus.PUBLISHED:
        raise CampaignValidationError(
            {"template_id": "Only published templates can be used in a campaign."}
        )
    return template


def prepare_authorization_scope(
    db: Session,
    org: Organization,
    campaign: Campaign,
    *,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
) -> dict[str, Any]:
    fields: dict[str, str] = {}
    template_id = campaign.template_id
    group_id = campaign.group_id
    raw_send_time = campaign.send_time
    if template_id is None or campaign.template_version is None:
        fields["template_id"] = "Choose a published template."
    if group_id is None:
        fields["group_id"] = "Choose a target group."
    if raw_send_time is None:
        fields["send_time"] = "Choose a send date and time."
    if fields:
        raise CampaignValidationError(fields)
    assert template_id is not None
    assert group_id is not None
    assert raw_send_time is not None

    group = _resolve_group(db, org.id, group_id)
    template = _resolve_template(db, org.id, template_id)

    if template.version != campaign.template_version:
        fields["template_id"] = (
            "The selected template version is no longer current. Choose the "
            "published version again."
        )

    send_time = ensure_utc(raw_send_time)
    start = ensure_utc(valid_from) if valid_from else utcnow()
    end = ensure_utc(valid_until) if valid_until else send_time + timedelta(days=7)
    if end <= start:
        fields["end_date"] = "The authorization end date must be after its start date."
    if send_time < start or send_time > end:
        fields["send_time"] = (
            "The send time must fall inside the authorization start and end dates."
        )

    if not domain_allowed(org, campaign.sending_domain):
        fields["sending_domain"] = (
            "The sending domain is not in this organization's allowlist."
        )

    count = target_count(db, group.id)
    if count < org.min_group_size:
        fields["target_count"] = (
            f"Reports need at least {org.min_group_size} recipients; this group "
            f"has {count}."
        )

    if fields:
        raise CampaignValidationError(fields)

    return {
        "group_id": group.id,
        "template_id": template.id,
        "template_version": template.version,
        "target_count": count,
        "sending_domain": campaign.sending_domain,
        "scheduled_send_time": send_time,
        "start_date": start,
        "end_date": end,
    }


def request_authorization(
    db: Session,
    org: Organization,
    campaign: Campaign,
    *,
    requested_by: uuid.UUID,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    note: str | None = None,
) -> Authorization:
    if campaign.status != CampaignStatus.DRAFT:
        raise CampaignConflictError(
            "campaign_not_editable",
            "Only draft campaigns can request authorization.",
        )
    scope = prepare_authorization_scope(
        db, org, campaign, valid_from=valid_from, valid_until=valid_until
    )
    for old in db.execute(
        select(Authorization).where(
            Authorization.campaign_id == campaign.id,
            Authorization.status.in_(
                [
                    AuthorizationStatus.REQUESTED,
                    AuthorizationStatus.APPROVED,
                ]
            ),
        )
    ).scalars():
        old.status = AuthorizationStatus.REVOKED
        old.revoked_at = utcnow()
        old.reason = old.reason or "Superseded by a new authorization request."
        db.add(old)

    auth = Authorization(
        org_id=org.id,
        campaign_id=campaign.id,
        requested_by=requested_by,
        group_id=scope["group_id"],
        template_id=scope["template_id"],
        template_version=scope["template_version"],
        target_count=scope["target_count"],
        sending_domain=scope["sending_domain"],
        scheduled_send_time=scope["scheduled_send_time"],
        start_date=scope["start_date"],
        end_date=scope["end_date"],
        status=AuthorizationStatus.REQUESTED,
        reason=note,
    )
    db.add(auth)
    campaign.status = CampaignStatus.PENDING_AUTHORIZATION
    campaign.template_version = scope["template_version"]
    db.add(campaign)
    db.flush()
    return auth


def approve_authorization(
    db: Session,
    org: Organization,
    auth: Authorization,
    *,
    approved_by: uuid.UUID,
    note: str | None = None,
) -> Authorization:
    if auth.status != AuthorizationStatus.REQUESTED:
        raise CampaignConflictError(
            "authorization_not_pending", "This authorization is not awaiting approval."
        )
    if effective_status(auth) == AuthorizationStatus.EXPIRED:
        auth.status = AuthorizationStatus.EXPIRED
        db.add(auth)
        db.flush()
        raise CampaignConflictError(
            "approval_expired", "This authorization request has expired."
        )
    if auth.requested_by is not None and str(auth.requested_by) == str(approved_by):
        raise CampaignConflictError(
            "separation_of_duties",
            "The person who requested authorization cannot approve it.",
        )
    auth.status = AuthorizationStatus.APPROVED
    auth.approved_by = approved_by
    auth.decided_at = utcnow()
    if note:
        auth.reason = note
    campaign = db.get(Campaign, auth.campaign_id)
    if campaign is not None:
        campaign.status = CampaignStatus.APPROVED
        db.add(campaign)
    db.add(auth)
    db.flush()
    return auth


def reject_authorization(
    db: Session,
    org: Organization,
    auth: Authorization,
    *,
    rejected_by: uuid.UUID,
    reason: str,
) -> Authorization:
    if auth.status != AuthorizationStatus.REQUESTED:
        raise CampaignConflictError(
            "authorization_not_pending", "This authorization is not awaiting approval."
        )
    auth.status = AuthorizationStatus.REJECTED
    auth.approved_by = rejected_by
    auth.decided_at = utcnow()
    auth.reason = reason
    campaign = db.get(Campaign, auth.campaign_id)
    if campaign is not None and campaign.status == CampaignStatus.PENDING_AUTHORIZATION:
        campaign.status = CampaignStatus.DRAFT
        db.add(campaign)
    db.add(auth)
    db.flush()
    return auth


def revoke_approved_for_scope_change(db: Session, campaign: Campaign) -> None:
    now = utcnow()
    rows = list(
        db.execute(
            select(Authorization).where(
                Authorization.campaign_id == campaign.id,
                Authorization.status == AuthorizationStatus.APPROVED,
            )
        ).scalars()
    )
    for row in rows:
        row.status = AuthorizationStatus.REVOKED
        row.revoked_at = now
        row.reason = "Campaign scope changed after approval; approval revoked."
        db.add(row)
    if rows:
        db.flush()


def scope_mismatches(
    db: Session, campaign: Campaign, auth: Authorization
) -> dict[str, str]:
    problems: dict[str, str] = {}
    if campaign.group_id != auth.group_id:
        problems["group_id"] = "The campaign group changed after approval."
    if campaign.template_id != auth.template_id:
        problems["template_id"] = "The campaign template changed after approval."
    if campaign.template_version != auth.template_version:
        problems["template_version"] = (
            "The campaign template version changed after approval."
        )
    if campaign.sending_domain != auth.sending_domain:
        problems["sending_domain"] = (
            "The campaign sending domain changed after approval."
        )
    if campaign.send_time is None or ensure_utc(campaign.send_time) != ensure_utc(
        auth.scheduled_send_time
    ):
        problems["send_time"] = "The campaign send date changed after approval."
    current = target_count(db, campaign.group_id)
    if current != auth.target_count:
        problems["target_count"] = (
            "The recipient count changed after approval. Request a new approval."
        )
    return problems


def launch_blockers(
    db: Session, org: Organization, campaign: Campaign
) -> dict[str, str]:
    problems: dict[str, str] = {}
    if campaign.status not in (CampaignStatus.APPROVED, CampaignStatus.SCHEDULED):
        if campaign.status == CampaignStatus.RUNNING:
            problems["status"] = "The campaign is already running."
        else:
            problems["status"] = "The campaign must be approved before launch."

    auth = latest_authorization(db, campaign.id)
    if auth is None or auth.status != AuthorizationStatus.APPROVED:
        problems["authorization"] = (
            "An approved authorization is required before launch."
        )
        return problems

    now = utcnow()
    if effective_status(auth, now) == AuthorizationStatus.EXPIRED or ensure_utc(
        auth.end_date
    ) < now:
        problems["expired"] = "The authorization has expired. Request a new approval."

    if auth.requested_by is not None and auth.approved_by is not None:
        if str(auth.requested_by) == str(auth.approved_by):
            problems["separation_of_duties"] = (
                "The requester and approver must be different people."
            )

    if not domain_allowed(org, campaign.sending_domain):
        problems["sending_domain"] = (
            "The sending domain is not in this organization's allowlist."
        )

    count = target_count(db, campaign.group_id)
    if count < org.min_group_size:
        problems["group_size"] = (
            f"Reports need at least {org.min_group_size} recipients; this group "
            f"has {count}."
        )

    if campaign.send_time is not None:
        send_time = ensure_utc(campaign.send_time)
        if send_time < ensure_utc(auth.start_date) or send_time > ensure_utc(
            auth.end_date
        ):
            problems["dates"] = (
                "The send time is outside the approved authorization window."
            )
    problems.update(scope_mismatches(db, campaign, auth))
    return problems


def _fill_placeholders(value: str, first_name: str) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name == "first_name":
            return first_name
        if name == "tracking_link":
            return DEFAULT_TRACKING_LINK
        return ""

    return _PLACEHOLDER_RE.sub(replace, value)


def allowed_test_recipients(user: User) -> set[str]:
    return {user.email.lower(), settings.SMTP_FROM.lower(), "sandbox@example.test"}


def build_test_message(
    template: Template, user: User, recipient: str
) -> tuple[str, str]:
    first_name = (user.display_name or "there").split()[0]
    subject = TEST_SUBJECT_PREFIX + _fill_placeholders(template.subject, first_name)
    body = TEST_NOTICE + "\n" + _fill_placeholders(template.body, first_name)
    return subject, body


def test_send(
    db: Session,
    org: Organization,
    campaign: Campaign,
    *,
    user: User,
    recipient: str | None = None,
) -> dict[str, Any]:
    if campaign.template_id is None:
        raise CampaignValidationError({"template_id": "Choose a template first."})
    template = db.get(Template, campaign.template_id)
    if template is None or template.org_id != org.id:
        raise CampaignValidationError({"template_id": "Template not found."})

    chosen = (recipient or settings.SMTP_FROM).strip().lower()
    if chosen not in allowed_test_recipients(user):
        raise CampaignValidationError(
            {
                "recipient": (
                    "Test sends may only go to your own address or the Mailpit "
                    "sandbox inbox."
                )
            }
        )
    domain = chosen.rsplit("@", 1)[-1]
    if not mail.is_sandbox_domain(domain):
        raise CampaignValidationError(
            {"recipient": "The test recipient must use a sandbox domain."}
        )

    subject, body = build_test_message(template, user, chosen)
    mail.send_mail_sandbox(chosen, subject, body)
    return {
        "ok": True,
        "recipient": chosen,
        "sandbox": True,
        "tracking_link_replaced": True,
    }
