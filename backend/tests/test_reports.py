"""M8 reporting: rates, suppression, dashboard parity, RBAC and safe CSV."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models import (
    Campaign,
    CampaignStatus,
    Group,
    GroupMember,
    Organization,
    Target,
    Template,
    TemplateDifficulty,
    TemplateStatus,
    TrackingEvent,
    TrackingEventType,
    TrackingLink,
    User,
    UserRole,
)
from app.services import tracking_service
from tests.conftest import login_as, session_csrf_token
from tests.test_campaigns import PASSWORD, _group, _make_user, _template

NOW = datetime.now(UTC)


def _campaign(
    db_session,
    organization: Organization,
    group: Group,
    template: Template,
    name: str,
    *,
    status: CampaignStatus = CampaignStatus.COMPLETED,
    created_by: User | None = None,
) -> Campaign:
    campaign = Campaign(
        org_id=organization.id,
        name=name,
        description="Reports test campaign",
        template_id=template.id,
        template_version=template.version,
        group_id=group.id,
        send_time=NOW - timedelta(days=2),
        sending_domain="example.test",
        status=status,
        created_by=created_by.id if created_by else None,
    )
    db_session.add(campaign)
    db_session.flush()
    tracking_service.ensure_tracking_links(db_session, campaign)
    db_session.commit()
    return campaign


def _record(
    db_session,
    campaign: Campaign,
    event_type: TrackingEventType,
    count: int,
    *,
    occurred_at: datetime = NOW,
) -> None:
    links = list(
        db_session.execute(
            select(TrackingLink)
            .join(Target, Target.id == TrackingLink.target_id)
            .where(TrackingLink.campaign_id == campaign.id)
            .order_by(Target.email.asc())
        ).scalars()
    )
    for link in links[:count]:
        tracking_service.record_event(
            db_session, link, event_type, occurred_at=occurred_at
        )
    db_session.commit()


def _seed_campaign_events(
    db_session,
    organization: Organization,
    *,
    name: str,
    group_members: int,
    status: CampaignStatus = CampaignStatus.COMPLETED,
) -> tuple[Campaign, Group]:
    admin = _make_user(
        db_session, organization, f"{name.lower().replace(' ', '-')}@example.test", UserRole.ADMIN
    )
    template = _template(db_session, organization, name=f"{name} template")
    group = _group(db_session, organization, f"{name} Group", members=group_members)
    campaign = _campaign(
        db_session,
        organization,
        group,
        template,
        name,
        status=status,
        created_by=admin,
    )
    _record(
        db_session, campaign, TrackingEventType.DELIVERED, group_members,
        occurred_at=NOW - timedelta(days=3),
    )
    return campaign, group


def _basis(db_session, organization: Organization, *, members: int = 5):
    admin = _make_user(db_session, organization, "reports-admin@example.test", UserRole.ADMIN)
    analyst = _make_user(db_session, organization, "reports-analyst@example.test", UserRole.ANALYST)
    employee = _make_user(db_session, organization, "reports-employee@example.test", UserRole.EMPLOYEE)
    template = _template(db_session, organization)
    group = _group(db_session, organization, "Eligible Group", members=members)
    return admin, analyst, employee, template, group


def test_report_rates_suppression_and_scope(db_session, client_factory, organization):
    admin, _analyst, _employee, template, group = _basis(db_session, organization)
    eligible = _campaign(
        db_session, organization, group, template, "Eligible campaign",
        status=CampaignStatus.RUNNING, created_by=admin,
    )
    _record(db_session, eligible, TrackingEventType.DELIVERED, 5)
    _record(db_session, eligible, TrackingEventType.CLICKED, 2)
    _record(db_session, eligible, TrackingEventType.REPORTED, 1)
    _record(db_session, eligible, TrackingEventType.QUIZ_COMPLETED, 1)

    small_group = _group(db_session, organization, "Tiny Group", members=3)
    small = _campaign(
        db_session, organization, small_group, template, "Suppressed campaign",
        created_by=admin,
    )
    _record(db_session, small, TrackingEventType.DELIVERED, 3)
    _record(db_session, small, TrackingEventType.CLICKED, 3)

    login_as(client_factory, admin.email, PASSWORD)

    selected = client_factory.get(
        "/api/v1/reports/summary", params={"campaign_id": str(eligible.id)}
    )
    assert selected.status_code == 200, selected.text
    payload = selected.json()
    assert payload["suppressed"] is False
    assert payload["summary"]["delivered"] == 5
    assert payload["summary"]["clicked"] == 2
    assert payload["summary"]["reported"] == 1
    assert payload["summary"]["quiz_completed"] == 1
    assert payload["summary"]["click_rate"] == 0.4
    assert payload["summary"]["report_rate"] == 0.2
    assert payload["summary"]["quiz_rate"] == 0.2
    assert [row["name"] for row in payload["groups"]] == ["Eligible Group"]

    everything = client_factory.get("/api/v1/reports/summary")
    assert everything.status_code == 200, everything.text
    all_payload = everything.json()
    assert all_payload["suppressed"] is False
    assert all_payload["summary"]["delivered"] == 5
    assert all_payload["summary"]["clicked"] == 2
    assert all_payload["suppressed_groups"] == 1
    assert "Tiny Group" not in everything.text
    assert all(row["name"] != "Tiny Group" for row in all_payload["groups"])

    hidden = client_factory.get(
        "/api/v1/reports/summary", params={"campaign_id": str(small.id)}
    )
    assert hidden.status_code == 200, hidden.text
    hidden_payload = hidden.json()
    assert hidden_payload["suppressed"] is True
    assert hidden_payload["summary"] is None
    assert hidden_payload["groups"] == []
    assert hidden_payload["trend"] == []


def test_dashboard_matches_all_campaign_report_and_active_count(
    db_session, client_factory, organization
):
    admin, _analyst, _employee, template, group = _basis(db_session, organization)
    running = _campaign(
        db_session, organization, group, template, "Running report campaign",
        status=CampaignStatus.RUNNING, created_by=admin,
    )
    _record(db_session, running, TrackingEventType.DELIVERED, 5)
    _record(db_session, running, TrackingEventType.CLICKED, 3)
    _record(db_session, running, TrackingEventType.REPORTED, 2)
    completed = _campaign(
        db_session, organization, group, template, "Completed report campaign",
        created_by=admin,
    )
    _record(db_session, completed, TrackingEventType.DELIVERED, 5)
    _record(db_session, completed, TrackingEventType.QUIZ_COMPLETED, 1)

    login_as(client_factory, admin.email, PASSWORD)
    dashboard = client_factory.get("/api/v1/dashboard")
    report = client_factory.get("/api/v1/reports/summary")
    assert dashboard.status_code == 200, dashboard.text
    assert report.status_code == 200, report.text
    dash = dashboard.json()
    summary = report.json()["summary"]
    assert dash["active_campaigns"] == 1
    assert dash["delivered"] == summary["delivered"] == 10
    assert dash["click_rate"] == summary["click_rate"]
    assert dash["report_rate"] == summary["report_rate"]
    assert dash["quiz_rate"] == summary["quiz_rate"]
    assert dash["has_data"] is True
    assert len(dash["recent_campaigns"]) == 2
    assert len(dash["trend"]) >= 1
    assert all("member" not in key for key in dash)


def test_dashboard_empty_org_is_zeroed(db_session, client_factory, organization):
    admin = _make_user(db_session, organization, "empty-admin@example.test", UserRole.ADMIN)
    login_as(client_factory, admin.email, PASSWORD)
    response = client_factory.get("/api/v1/dashboard")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["active_campaigns"] == 0
    assert payload["delivered"] == 0
    assert payload["click_rate"] == 0
    assert payload["report_rate"] == 0
    assert payload["has_data"] is False
    assert payload["recent_campaigns"] == []
    assert payload["trend"] == []


def test_reports_rbac_and_organization_isolation(
    db_session, client_factory, organization
):
    _admin, analyst, employee, template, group = _basis(db_session, organization)
    campaign = _campaign(db_session, organization, group, template, "Own campaign")
    _record(db_session, campaign, TrackingEventType.DELIVERED, 5)

    assert client_factory.get("/api/v1/reports/campaigns").status_code == 401
    assert client_factory.get("/api/v1/dashboard").status_code == 401

    login_as(client_factory, employee.email, PASSWORD)
    assert client_factory.get("/api/v1/reports/campaigns").status_code == 403
    assert client_factory.get("/api/v1/reports/summary").status_code == 403
    assert client_factory.get("/api/v1/dashboard").status_code == 200
    assert (
        client_factory.post("/api/v1/reports/export", json={}).status_code == 403
    )

    login_as(client_factory, analyst.email, PASSWORD)
    allowed = client_factory.get("/api/v1/reports/campaigns")
    assert allowed.status_code == 200, allowed.text
    assert [row["id"] for row in allowed.json()["campaigns"]] == [str(campaign.id)]

    other_org = Organization(
        name="Other Organization",
        slug="other-org",
        primary_domain="other.test",
    )
    db_session.add(other_org)
    db_session.flush()
    other_template = Template(
        org_id=other_org.id,
        family_id=uuid.uuid4(),
        version=1,
        name="Other template",
        sender="Other <other@other.test>",
        subject="Other",
        body="Other {{tracking_link}}",
        difficulty=TemplateDifficulty.EASY,
        attack_technique_id="none",
        lure_type="benign_control",
        status=TemplateStatus.PUBLISHED,
    )
    db_session.add(other_template)
    db_session.flush()
    other_group = Group(org_id=other_org.id, name="Other group")
    db_session.add(other_group)
    db_session.flush()
    for index in range(5):
        target = Target(
            org_id=other_org.id,
            email=f"other-{index}@other.test",
            display_name=f"Other {index}",
        )
        db_session.add(target)
        db_session.flush()
        db_session.add(GroupMember(group_id=other_group.id, target_id=target.id))
    other_campaign = Campaign(
        org_id=other_org.id,
        name="Other campaign",
        template_id=other_template.id,
        template_version=1,
        group_id=other_group.id,
        sending_domain="other.test",
        status=CampaignStatus.COMPLETED,
    )
    db_session.add(other_campaign)
    db_session.commit()

    campaigns = client_factory.get("/api/v1/reports/campaigns")
    assert campaigns.status_code == 200
    assert "Other campaign" not in campaigns.text
    hidden = client_factory.get(
        "/api/v1/reports/summary", params={"campaign_id": str(other_campaign.id)}
    )
    assert hidden.status_code == 404


def test_csv_export_requires_csrf_and_escapes_formulas(
    db_session, client_factory, organization
):
    admin, _analyst, _employee, template, group = _basis(db_session, organization)
    group.name = "=2+2"
    db_session.flush()
    campaign = _campaign(
        db_session, organization, group, template, "=cmd|' /C calc'!A0"
    )
    _record(db_session, campaign, TrackingEventType.DELIVERED, 5)
    login_as(client_factory, admin.email, PASSWORD)

    denied = client_factory.post("/api/v1/reports/export", json={})
    assert denied.status_code == 403

    headers = {"X-CSRF-Token": session_csrf_token(client_factory)}
    exported = client_factory.post(
        "/api/v1/reports/export",
        json={"campaign_id": str(campaign.id)},
        headers=headers,
    )
    assert exported.status_code == 200, exported.text
    assert exported.headers["content-type"].startswith("text/csv")
    body = exported.text
    assert "'=2+2" in body
    assert "'=cmd|' /C calc'!A0" in body
    assert "\r" not in body.replace("\r\n", "\n")


def test_quiz_completion_is_idempotent_and_ignores_bad_tokens(
    db_session, client_factory, organization
):
    _admin, _analyst, _employee, template, group = _basis(db_session, organization)
    campaign = _campaign(db_session, organization, group, template, "Quiz campaign")
    link = db_session.execute(
        select(TrackingLink).where(TrackingLink.campaign_id == campaign.id)
    ).scalars().first()
    assert link is not None

    first = client_factory.post(f"/api/v1/quiz/{link.token}/complete")
    second = client_factory.post(f"/api/v1/quiz/{link.token}/complete")
    invalid = client_factory.post("/api/v1/quiz/not-a-token/complete")
    assert first.status_code == 200, first.text
    assert first.json() == {"completed": True, "recorded": True}
    assert second.status_code == 200
    assert second.json() == {"completed": True, "recorded": False}
    assert invalid.status_code == 200
    assert invalid.json() == {"completed": True, "recorded": False}

    events = list(
        db_session.execute(
            select(TrackingEvent).where(
                TrackingEvent.tracking_link_id == link.id,
                TrackingEvent.event_type == TrackingEventType.QUIZ_COMPLETED.value,
            )
        ).scalars()
    )
    assert len(events) == 1
    assert events[0].event_type == "quiz_completed"


def test_csv_cell_escapes_whitespace_leading_formula():
    from app.services.reports_service import csv_cell

    assert csv_cell("=SUM(A1:A2)") == "'=SUM(A1:A2)"
    assert csv_cell(" +cmd") == "' +cmd"
    assert csv_cell(None) == ""
    assert csv_cell("Finance") == "Finance"
