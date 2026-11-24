"""Organization-scoped awareness reporting and dashboard aggregates.

Every aggregate in this module goes through the same eligible-group rule:
a campaign can only contribute when its group has at least
``Organization.min_group_size`` members. Suppressed groups are counted but
never named or included in chart data.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import distinct, func, or_, select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign, CampaignStatus
from app.models.group import Group, GroupMember
from app.models.organization import Organization
from app.models.tracking import TrackingEvent, TrackingEventType

ACTIVE_STATUSES = (CampaignStatus.SCHEDULED, CampaignStatus.RUNNING)
EVENT_TYPES = tuple(event.value for event in TrackingEventType)


def _group_sizes():
    return (
        select(
            GroupMember.group_id.label("group_id"),
            func.count(GroupMember.id).label("member_count"),
        )
        .group_by(GroupMember.group_id)
        .subquery()
    )


def _eligible_campaign_ids(
    db: Session, org_id: uuid.UUID, min_group_size: int
) -> list[uuid.UUID]:
    sizes = _group_sizes()
    return list(
        db.execute(
            select(Campaign.id)
            .join(sizes, sizes.c.group_id == Campaign.group_id)
            .where(
                Campaign.org_id == org_id,
                sizes.c.member_count >= min_group_size,
            )
        ).scalars()
    )


def _event_totals(
    db: Session, org_id: uuid.UUID, campaign_ids: list[uuid.UUID]
) -> dict[str, int]:
    if not campaign_ids:
        return {}
    rows = db.execute(
        select(
            TrackingEvent.event_type,
            func.count(distinct(TrackingEvent.tracking_link_id)),
        )
        .where(
            TrackingEvent.org_id == org_id,
            TrackingEvent.campaign_id.in_(campaign_ids),
        )
        .group_by(TrackingEvent.event_type)
    ).all()
    return {event_type: int(count) for event_type, count in rows}


def _rates(delivered: int, clicked: int, reported: int, completed: int) -> dict[str, float]:
    denominator = delivered if delivered > 0 else 0
    return {
        "click_rate": (clicked / denominator) if denominator else 0.0,
        "report_rate": (reported / denominator) if denominator else 0.0,
        "quiz_rate": (completed / denominator) if denominator else 0.0,
    }


def _summary(
    db: Session, org_id: uuid.UUID, campaign_ids: list[uuid.UUID]
) -> dict[str, Any]:
    totals = _event_totals(db, org_id, campaign_ids)
    delivered = totals.get(TrackingEventType.DELIVERED.value, 0)
    clicked = totals.get(TrackingEventType.CLICKED.value, 0)
    reported = totals.get(TrackingEventType.REPORTED.value, 0)
    completed = totals.get(TrackingEventType.QUIZ_COMPLETED.value, 0)
    return {
        "delivered": delivered,
        "clicked": clicked,
        "reported": reported,
        "quiz_completed": completed,
        **_rates(delivered, clicked, reported, completed),
    }


def _groups(
    db: Session,
    org_id: uuid.UUID,
    campaign_ids: list[uuid.UUID],
    min_group_size: int,
) -> list[dict[str, Any]]:
    if not campaign_ids:
        return []
    sizes = _group_sizes()
    rows = db.execute(
        select(
            Group.id,
            Group.name,
            Group.department,
            TrackingEvent.event_type,
            func.count(distinct(TrackingEvent.tracking_link_id)),
        )
        .join(Campaign, Campaign.id == TrackingEvent.campaign_id)
        .join(Group, Group.id == Campaign.group_id)
        .join(sizes, sizes.c.group_id == Group.id)
        .where(
            TrackingEvent.org_id == org_id,
            TrackingEvent.campaign_id.in_(campaign_ids),
            sizes.c.member_count >= min_group_size,
        )
        .group_by(
            Group.id,
            Group.name,
            Group.department,
            TrackingEvent.event_type,
        )
    ).all()

    grouped: dict[uuid.UUID, dict[str, Any]] = {}
    for group_id, name, department, event_type, count in rows:
        row = grouped.setdefault(
            group_id,
            {
                "id": str(group_id),
                "name": name,
                "department": department,
                "delivered": 0,
                "clicked": 0,
                "reported": 0,
                "quiz_completed": 0,
                "click_rate": 0.0,
                "report_rate": 0.0,
                "quiz_rate": 0.0,
            },
        )
        if event_type in (
            TrackingEventType.DELIVERED.value,
            TrackingEventType.CLICKED.value,
            TrackingEventType.REPORTED.value,
            TrackingEventType.QUIZ_COMPLETED.value,
        ):
            row[event_type] = int(count)

    result = list(grouped.values())
    for row in result:
        row.update(
            _rates(
                int(row["delivered"]),
                int(row["clicked"]),
                int(row["reported"]),
                int(row["quiz_completed"]),
            )
        )
    result.sort(key=lambda item: str(item["name"]).lower())
    return result


def _trend(
    db: Session, org_id: uuid.UUID, campaign_ids: list[uuid.UUID]
) -> list[dict[str, Any]]:
    if not campaign_ids:
        return []
    day = func.date(func.timezone("UTC", TrackingEvent.occurred_at)).label("day")
    rows = db.execute(
        select(
            day,
            TrackingEvent.event_type,
            func.count(distinct(TrackingEvent.tracking_link_id)),
        )
        .where(
            TrackingEvent.org_id == org_id,
            TrackingEvent.campaign_id.in_(campaign_ids),
        )
        .group_by(day, TrackingEvent.event_type)
        .order_by(day)
    ).all()

    points: dict[str, dict[str, Any]] = {}
    for day_value, event_type, count in rows:
        key = day_value.isoformat() if hasattr(day_value, "isoformat") else str(day_value)
        point = points.setdefault(
            key,
            {
                "date": key,
                "delivered": 0,
                "clicked": 0,
                "reported": 0,
                "quiz_completed": 0,
                "click_rate": 0.0,
                "report_rate": 0.0,
            },
        )
        if event_type in (
            TrackingEventType.DELIVERED.value,
            TrackingEventType.CLICKED.value,
            TrackingEventType.REPORTED.value,
            TrackingEventType.QUIZ_COMPLETED.value,
        ):
            point[event_type] = int(count)

    result = sorted(points.values(), key=lambda item: item["date"])
    cumulative_delivered = 0
    cumulative_clicked = 0
    cumulative_reported = 0
    for point in result:
        cumulative_delivered += int(point["delivered"])
        cumulative_clicked += int(point["clicked"])
        cumulative_reported += int(point["reported"])
        if cumulative_delivered:
            point["click_rate"] = cumulative_clicked / cumulative_delivered
            point["report_rate"] = cumulative_reported / cumulative_delivered
    return result


def _suppressed_group_count(
    db: Session,
    org_id: uuid.UUID,
    campaign_ids: list[uuid.UUID],
    min_group_size: int,
) -> int:
    if not campaign_ids:
        return 0
    sizes = _group_sizes()
    value = db.execute(
        select(func.count(distinct(Group.id)))
        .select_from(TrackingEvent)
        .join(Campaign, Campaign.id == TrackingEvent.campaign_id)
        .join(Group, Group.id == Campaign.group_id)
        .outerjoin(sizes, sizes.c.group_id == Group.id)
        .where(
            TrackingEvent.org_id == org_id,
            TrackingEvent.campaign_id.in_(campaign_ids),
            or_(
                sizes.c.member_count < min_group_size,
                sizes.c.member_count.is_(None),
            ),
        )
    ).scalar_one()
    return int(value or 0)


def _campaign_group(
    db: Session, campaign: Campaign
) -> tuple[Group | None, int | None]:
    if campaign.group_id is None:
        return None, None
    group = db.get(Group, campaign.group_id)
    if group is None or group.org_id != campaign.org_id:
        return None, None
    member_count = db.execute(
        select(func.count(GroupMember.id)).where(
            GroupMember.group_id == campaign.group_id
        )
    ).scalar_one()
    return group, int(member_count)


def list_campaigns(
    db: Session, org_id: uuid.UUID, min_group_size: int
) -> list[dict[str, Any]]:
    sizes = _group_sizes()
    rows = db.execute(
        select(Campaign, Group, sizes.c.member_count)
        .outerjoin(Group, Group.id == Campaign.group_id)
        .outerjoin(sizes, sizes.c.group_id == Campaign.group_id)
        .where(Campaign.org_id == org_id)
        .order_by(Campaign.updated_at.desc(), Campaign.id.desc())
    ).all()
    campaigns = []
    for campaign, group, member_count in rows:
        count = int(member_count) if member_count is not None else None
        campaigns.append(
            {
                "id": str(campaign.id),
                "name": campaign.name,
                "status": campaign.status.value,
                "group_id": str(group.id) if group is not None else None,
                "group_name": group.name if group is not None else None,
                "member_count": count,
                "suppressed": group is None or count is None or count < min_group_size,
            }
        )
    return campaigns


def campaign_summary(
    db: Session, org: Organization, campaign_id: str | None = None
) -> dict[str, Any] | None:
    campaign: Campaign | None = None
    if campaign_id:
        try:
            cid = uuid.UUID(campaign_id)
        except (TypeError, ValueError):
            return None
        campaign = db.get(Campaign, cid)
        if campaign is None or campaign.org_id != org.id:
            return None

    min_group_size = org.min_group_size
    scope: dict[str, Any] = {
        "campaign_id": None,
        "campaign_name": "All campaigns",
        "group_id": None,
        "group_name": None,
    }
    campaign_ids: list[uuid.UUID]

    if campaign is not None:
        group, member_count = _campaign_group(db, campaign)
        scope.update(
            {
                "campaign_id": str(campaign.id),
                "campaign_name": campaign.name,
                "group_id": str(group.id) if group is not None else None,
                "group_name": group.name if group is not None else None,
            }
        )
        if group is None or member_count is None or member_count < min_group_size:
            return {
                "generated_at": datetime.now(UTC).isoformat(),
                "scope": scope,
                "min_group_size": min_group_size,
                "suppressed": True,
                "suppressed_groups": 1,
                "summary": None,
                "groups": [],
                "trend": [],
            }
        campaign_ids = [campaign.id]
    else:
        campaign_ids = _eligible_campaign_ids(db, org.id, min_group_size)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": scope,
        "min_group_size": min_group_size,
        "suppressed": False,
        "suppressed_groups": _suppressed_group_count(
            db, org.id, _event_totals_campaign_ids(db, org.id), min_group_size
        )
        if campaign is None
        else 0,
        "summary": _summary(db, org.id, campaign_ids),
        "groups": _groups(db, org.id, campaign_ids, min_group_size),
        "trend": _trend(db, org.id, campaign_ids),
    }


def _event_totals_campaign_ids(db: Session, org_id: uuid.UUID) -> list[uuid.UUID]:
    """All campaigns that have events, including suppressed ones."""
    return list(
        db.execute(
            select(distinct(TrackingEvent.campaign_id)).where(
                TrackingEvent.org_id == org_id
            )
        ).scalars()
    )


def dashboard(db: Session, org: Organization) -> dict[str, Any]:
    data = campaign_summary(db, org)
    assert data is not None
    summary = data["summary"] or {
        "delivered": 0,
        "clicked": 0,
        "reported": 0,
        "quiz_completed": 0,
        "click_rate": 0.0,
        "report_rate": 0.0,
        "quiz_rate": 0.0,
    }

    active_campaigns = int(
        db.execute(
            select(func.count(Campaign.id)).where(
                Campaign.org_id == org.id,
                Campaign.status.in_(ACTIVE_STATUSES),
            )
        ).scalar_one()
    )

    sizes = _group_sizes()
    recent_rows = db.execute(
        select(Campaign, Group.name, sizes.c.member_count)
        .outerjoin(Group, Group.id == Campaign.group_id)
        .outerjoin(sizes, sizes.c.group_id == Campaign.group_id)
        .where(Campaign.org_id == org.id)
        .order_by(Campaign.updated_at.desc(), Campaign.id.desc())
        .limit(5)
    ).all()

    recent_ids = [campaign.id for campaign, _group_name, _count in recent_rows]
    totals_by_campaign: dict[uuid.UUID, dict[str, int]] = {}
    if recent_ids:
        event_rows = db.execute(
            select(
                TrackingEvent.campaign_id,
                TrackingEvent.event_type,
                func.count(distinct(TrackingEvent.tracking_link_id)),
            )
            .where(
                TrackingEvent.org_id == org.id,
                TrackingEvent.campaign_id.in_(recent_ids),
            )
            .group_by(TrackingEvent.campaign_id, TrackingEvent.event_type)
        ).all()
        for campaign_pk, event_type, count in event_rows:
            totals_by_campaign.setdefault(campaign_pk, {})[event_type] = int(count)

    recent = []
    for campaign, group_name, member_count in recent_rows:
        count = int(member_count) if member_count is not None else None
        suppressed = (
            group_name is None or count is None or count < org.min_group_size
        )
        totals = totals_by_campaign.get(campaign.id, {})
        delivered = totals.get(TrackingEventType.DELIVERED.value, 0)
        clicked = totals.get(TrackingEventType.CLICKED.value, 0)
        reported = totals.get(TrackingEventType.REPORTED.value, 0)
        completed = totals.get(TrackingEventType.QUIZ_COMPLETED.value, 0)
        rates = _rates(delivered, clicked, reported, completed)
        recent.append(
            {
                "id": str(campaign.id),
                "name": campaign.name,
                "status": campaign.status.value,
                "group_name": group_name,
                "delivered": None if suppressed else delivered,
                "click_rate": None if suppressed else rates["click_rate"],
                "report_rate": None if suppressed else rates["report_rate"],
                "suppressed": suppressed,
            }
        )

    return {
        "generated_at": data["generated_at"],
        "active_campaigns": active_campaigns,
        "delivered": summary["delivered"],
        "click_rate": summary["click_rate"],
        "report_rate": summary["report_rate"],
        "quiz_rate": summary["quiz_rate"],
        "has_data": summary["delivered"] > 0,
        "min_group_size": org.min_group_size,
        "suppressed_groups": data["suppressed_groups"],
        "trend": data["trend"],
        "recent_campaigns": recent,
    }


def csv_cell(value: Any) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    text = text.replace("\r", " ").replace("\n", " ")
    if text.lstrip()[:1] in ("=", "+", "-", "@", "\t"):
        return "'" + text
    return text


def export_csv(data: dict[str, Any]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "scope",
            "campaign",
            "group",
            "department",
            "delivered",
            "clicked",
            "quiz_completed",
            "reported",
            "click_rate",
            "report_rate",
        ]
    )
    campaign_name = data["scope"]["campaign_name"]
    summary = data["summary"]
    if summary is None:
        writer.writerow(
            [
                "suppressed",
                csv_cell(campaign_name),
                "Reporting suppressed",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ]
        )
        return buffer.getvalue()

    writer.writerow(
        [
            "summary",
            csv_cell(campaign_name),
            "All eligible groups",
            "",
            summary["delivered"],
            summary["clicked"],
            summary["quiz_completed"],
            summary["reported"],
            f"{summary['click_rate']:.4f}",
            f"{summary['report_rate']:.4f}",
        ]
    )
    for group in data["groups"]:
        writer.writerow(
            [
                "group",
                csv_cell(campaign_name),
                csv_cell(group["name"]),
                csv_cell(group["department"]),
                group["delivered"],
                group["clicked"],
                group["quiz_completed"],
                group["reported"],
                f"{group['click_rate']:.4f}",
                f"{group['report_rate']:.4f}",
            ]
        )
    return buffer.getvalue()
