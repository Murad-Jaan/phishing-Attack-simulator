"""Idempotent demo campaign dataset for local dashboards and demos.

Run after ``seed_dev``. This creates one 8-person sandbox group, a completed
campaign with realistic awareness events and a currently running campaign.
Nothing here contacts a real address.
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign, CampaignStatus
from app.models.group import Group, GroupMember
from app.models.organization import Organization
from app.models.target import Target
from app.models.template import Template, TemplateStatus
from app.models.tracking import TrackingEventType, TrackingLink
from app.models.user import User
from app.services import tracking_service

GROUP_NAME = "Demo Finance Team"
CAMPAIGN_NAMES = (
    "Demo awareness: invoice review",
    "Demo awareness: travel policy update",
)
TARGET_COUNT = 8


def _guard_production() -> None:
    if os.getenv("APP_ENV", "development") == "production" or (
        os.getenv("ENV", "development") == "production"
    ):
        print("ERROR: Cannot run demo data seed in production")
        sys.exit(1)


def _targets(db: Session, org: Organization) -> list[Target]:
    targets = []
    for index in range(1, TARGET_COUNT + 1):
        email = f"demo-finance-{index:02d}@example.test"
        target = db.execute(
            select(Target).where(Target.org_id == org.id, Target.email == email)
        ).scalar_one_or_none()
        if target is None:
            target = Target(
                org_id=org.id,
                email=email,
                display_name=f"Demo Finance {index:02d}",
            )
            db.add(target)
            db.flush()
        targets.append(target)
    return targets


def _group(db: Session, org: Organization, targets: list[Target]) -> Group:
    group = db.execute(
        select(Group).where(Group.org_id == org.id, Group.name == GROUP_NAME)
    ).scalar_one_or_none()
    if group is None:
        group = Group(
            org_id=org.id,
            name=GROUP_NAME,
            department="Finance",
            description="Clearly labelled demo recipients for reports and dashboards.",
        )
        db.add(group)
        db.flush()
    for target in targets:
        exists = db.execute(
            select(GroupMember.id).where(
                GroupMember.group_id == group.id,
                GroupMember.target_id == target.id,
            )
        ).scalar_one_or_none()
        if exists is None:
            db.add(GroupMember(group_id=group.id, target_id=target.id))
    db.flush()
    return group


def _campaign(
    db: Session,
    org: Organization,
    group: Group,
    template: Template,
    admin: User | None,
    name: str,
    status: CampaignStatus,
    send_time: datetime,
) -> Campaign | None:
    existing = db.execute(
        select(Campaign).where(Campaign.org_id == org.id, Campaign.name == name)
    ).scalar_one_or_none()
    if existing is not None:
        print(f"Demo campaign already exists, skipping: {name}")
        return None
    campaign = Campaign(
        org_id=org.id,
        name=name,
        description="Seeded demo data. Sandbox recipients only.",
        template_id=template.id,
        template_version=template.version,
        group_id=group.id,
        send_time=send_time,
        sending_domain="example.test",
        status=status,
        created_by=admin.id if admin is not None else None,
    )
    db.add(campaign)
    db.flush()
    tracking_service.ensure_tracking_links(db, campaign)
    return campaign


def _record(
    db: Session,
    campaign: Campaign,
    event_type: TrackingEventType,
    target_numbers: range,
    occurred_at: datetime,
) -> None:
    links = list(
        db.execute(
            select(TrackingLink)
            .join(Target, Target.id == TrackingLink.target_id)
            .where(TrackingLink.campaign_id == campaign.id)
            .order_by(Target.email.asc())
        ).scalars()
    )
    for number in target_numbers:
        if number - 1 < len(links):
            tracking_service.record_event(
                db,
                links[number - 1],
                event_type,
                occurred_at=occurred_at,
            )


def seed_demo(db: Session) -> None:
    _guard_production()
    org = db.execute(
        select(Organization).where(Organization.slug == "demo-org")
    ).scalar_one_or_none()
    if org is None or not org.is_demo:
        print("ERROR: Run `make seed` first to create the demo organization")
        sys.exit(1)

    template = db.execute(
        select(Template)
        .where(Template.org_id == org.id, Template.status == TemplateStatus.PUBLISHED)
        .order_by(Template.name.asc())
        .limit(1)
    ).scalar_one_or_none()
    if template is None:
        print("ERROR: No published demo template found; run `make seed` first")
        sys.exit(1)

    admin = db.execute(
        select(User).where(
            User.org_id == org.id, User.email == "demo-admin-1@example.test"
        )
    ).scalar_one_or_none()
    targets = _targets(db, org)
    group = _group(db, org, targets)
    now = datetime.now(UTC)

    completed = _campaign(
        db,
        org,
        group,
        template,
        admin,
        CAMPAIGN_NAMES[0],
        CampaignStatus.COMPLETED,
        now - timedelta(days=12),
    )
    if completed is not None:
        _record(
            db,
            completed,
            TrackingEventType.DELIVERED,
            range(1, TARGET_COUNT + 1),
            now - timedelta(days=10),
        )
        _record(
            db,
            completed,
            TrackingEventType.CLICKED,
            range(1, 4),
            now - timedelta(days=9),
        )
        _record(
            db,
            completed,
            TrackingEventType.REPORTED,
            range(1, 3),
            now - timedelta(days=9),
        )
        _record(
            db,
            completed,
            TrackingEventType.QUIZ_COMPLETED,
            range(1, 3),
            now - timedelta(days=8),
        )
        print(f"Created completed demo campaign: {completed.name}")

    running = _campaign(
        db,
        org,
        group,
        template,
        admin,
        CAMPAIGN_NAMES[1],
        CampaignStatus.RUNNING,
        now - timedelta(days=1),
    )
    if running is not None:
        _record(
            db,
            running,
            TrackingEventType.DELIVERED,
            range(1, 7),
            now - timedelta(days=1),
        )
        _record(
            db,
            running,
            TrackingEventType.CLICKED,
            range(1, 3),
            now - timedelta(hours=18),
        )
        print(f"Created running demo campaign: {running.name}")

    db.commit()
    print("Demo dataset ready: 1 group, 8 sandbox targets, 2 campaigns")


if __name__ == "__main__":
    from app.db import SessionLocal

    session = SessionLocal()
    try:
        seed_demo(session)
    finally:
        session.close()
