"""Tracking links, append-only awareness events and safe click handling."""

from __future__ import annotations

import re
import secrets
import uuid
from datetime import datetime
from typing import Any
from urllib.parse import quote, urlsplit

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.campaign import Campaign
from app.models.group import GroupMember
from app.models.target import Target
from app.models.template import Template
from app.models.tracking import TrackingEvent, TrackingEventType, TrackingLink

TOKEN_BYTES = 32
MAX_TOKEN_LENGTH = 64

BOT_USER_AGENT_RE = re.compile(
    r"(?:bot\b|crawler|spider|slurp|facebookexternalhit|bingpreview|whatsapp|"
    r"telegrambot|python-requests|curl/|wget/|httpclient|okhttp|scanner|monitor)",
    re.IGNORECASE,
)

DEFAULT_AWARENESS_RED_FLAGS: tuple[dict[str, str], ...] = (
    {
        "label": "Urgent or threatening language",
        "explanation": "Real organizations rarely demand immediate action under threat of loss.",
    },
    {
        "label": "Unexpected request",
        "explanation": "A message asking you to open a link or sign in when you did not expect it is a warning sign.",
    },
    {
        "label": "Sender address does not match",
        "explanation": "Check the full sender address, not just the display name.",
    },
    {
        "label": "Link asks for credentials",
        "explanation": "Legitimate services do not ask for your password through an email link.",
    },
)


def new_token() -> str:
    """Return an unguessable URL-safe token with at least 256 bits of entropy."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def _clean_base(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = urlsplit(value.strip())
    except ValueError:
        return None
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def base_from_request(request: Request) -> str | None:
    """Derive the public origin a staff member used to reach the app."""
    origin = _clean_base(request.headers.get("origin"))
    if origin is not None:
        return origin
    referer = request.headers.get("referer")
    if referer:
        try:
            parsed = urlsplit(referer)
        except ValueError:
            return None
        if parsed.scheme and parsed.netloc:
            return _clean_base(f"{parsed.scheme}://{parsed.netloc}")
    return None


def tracking_base(campaign: Campaign) -> str:
    return (
        _clean_base(campaign.tracking_base_url)
        or _clean_base(settings.TRACKING_BASE_URL)
        or _clean_base(settings.APP_BASE_URL)
        or "http://127.0.0.1:3000"
    )


def tracking_url(campaign: Campaign, token: str) -> str:
    return f"{tracking_base(campaign)}/t/{quote(token, safe='')}"


def find_link(db: Session, token: str) -> TrackingLink | None:
    if not token or len(token) > MAX_TOKEN_LENGTH:
        return None
    return db.execute(
        select(TrackingLink).where(TrackingLink.token == token)
    ).scalar_one_or_none()


def lock_link(db: Session, token: str) -> TrackingLink | None:
    """Lock one link row so concurrent repeat clicks cannot double-record."""
    if not token or len(token) > MAX_TOKEN_LENGTH:
        return None
    return db.execute(
        select(TrackingLink)
        .where(TrackingLink.token == token)
        .with_for_update()
    ).scalar_one_or_none()


def is_bot(user_agent: str | None) -> bool:
    if not user_agent:
        return False
    return bool(BOT_USER_AGENT_RE.search(user_agent))


def ensure_tracking_links(db: Session, campaign: Campaign) -> int:
    """Create one durable token for each target, without duplicating rows."""
    if campaign.group_id is None:
        return 0
    existing = set(
        db.execute(
            select(TrackingLink.target_id).where(
                TrackingLink.campaign_id == campaign.id
            )
        ).scalars()
    )
    target_ids = list(
        db.execute(
            select(Target.id)
            .join(GroupMember, GroupMember.target_id == Target.id)
            .where(GroupMember.group_id == campaign.group_id)
            .order_by(Target.email.asc(), Target.id.asc())
        ).scalars()
    )
    created = 0
    for target_id in target_ids:
        if target_id in existing:
            continue
        result = db.execute(
            insert(TrackingLink)
            .values(
                org_id=campaign.org_id,
                campaign_id=campaign.id,
                target_id=target_id,
                token=new_token(),
            )
            .on_conflict_do_nothing()
        )
        created += int(result.rowcount or 0)
    if created:
        db.flush()
    return created


def record_event(
    db: Session,
    link: TrackingLink,
    event_type: TrackingEventType,
    *,
    occurred_at: datetime | None = None,
) -> bool:
    """Append an event unless the same link already has that event type."""
    exists = db.execute(
        select(TrackingEvent.id).where(
            TrackingEvent.tracking_link_id == link.id,
            TrackingEvent.event_type == event_type.value,
        )
    ).scalar_one_or_none()
    if exists is not None:
        return False
    event = TrackingEvent(
        org_id=link.org_id,
        campaign_id=link.campaign_id,
        tracking_link_id=link.id,
        event_type=event_type.value,
    )
    if occurred_at is not None:
        event.occurred_at = occurred_at
    db.add(event)
    db.flush()
    return True


def record_click(db: Session, token: str, user_agent: str | None) -> TrackingLink | None:
    link = lock_link(db, token)
    if link is None or is_bot(user_agent):
        return link
    record_event(db, link, TrackingEventType.CLICKED)
    return link


def record_delivered(db: Session, link: TrackingLink) -> bool:
    return record_event(db, link, TrackingEventType.DELIVERED)


def awareness_red_flags(db: Session, token: str) -> list[dict[str, str]]:
    link = find_link(db, token)
    if link is None:
        return [dict(item) for item in DEFAULT_AWARENESS_RED_FLAGS]
    campaign = db.get(Campaign, link.campaign_id)
    template = (
        db.get(Template, campaign.template_id)
        if campaign is not None and campaign.template_id is not None
        else None
    )
    if template is None or template.org_id != link.org_id:
        return [dict(item) for item in DEFAULT_AWARENESS_RED_FLAGS]
    flags = [
        {"label": flag.label, "explanation": flag.explanation}
        for flag in template.red_flags
    ]
    return flags or [dict(item) for item in DEFAULT_AWARENESS_RED_FLAGS]


def link_for_token(db: Session, token: str) -> TrackingLink | None:
    return find_link(db, token)


def event_counts(db: Session, campaign_id: uuid.UUID) -> dict[str, int]:
    rows = db.execute(
        select(TrackingEvent.event_type, TrackingEvent.id).where(
            TrackingEvent.campaign_id == campaign_id
        )
    ).all()
    counts: dict[str, int] = {}
    for event_type, _event_id in rows:
        counts[event_type] = counts.get(event_type, 0) + 1
    return counts


def public_link_payload(link: TrackingLink, campaign: Campaign | None) -> dict[str, Any]:
    return {
        "campaign_id": str(link.campaign_id),
        "target_id": str(link.target_id),
        "tracking_base_url": tracking_base(campaign) if campaign is not None else None,
    }
