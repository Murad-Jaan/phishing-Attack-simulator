"""Phase 3 tracking: unguessable tokens, per-target sends, safe clicks and Mailpit."""

from __future__ import annotations

import os
import time
import uuid
from contextlib import nullcontext
from urllib.parse import urlsplit

import httpx
from sqlalchemy import func, inspect, select

from app.models import (
    Campaign,
    CampaignSend,
    CampaignSendStatus,
    CampaignStatus,
    Target,
    TemplateRedFlag,
    TrackingEvent,
    TrackingEventType,
    TrackingLink,
)
from app.services import tracking_service
from app.worker import tasks
from tests.conftest import login_as
from tests.test_campaigns import (
    PASSWORD,
    _approved_campaign,
    _csrf,
    _group,
    _setup,
    _template,
)

MAILPIT_URL = os.getenv("MAILPIT_API_URL", "http://mailpit:8025")
CHROME_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _links(db_session, campaign_id: str) -> list[TrackingLink]:
    db_session.expire_all()
    return list(
        db_session.execute(
            select(TrackingLink)
            .where(TrackingLink.campaign_id == campaign_id)
            .order_by(TrackingLink.target_id)
        ).scalars()
    )


def _sends(db_session, campaign_id: str) -> list[CampaignSend]:
    db_session.expire_all()
    return list(
        db_session.execute(
            select(CampaignSend)
            .where(CampaignSend.campaign_id == campaign_id)
            .order_by(CampaignSend.target_id)
        ).scalars()
    )


def _events(
    db_session, campaign_id: str, event_type: TrackingEventType | None = None
) -> list[TrackingEvent]:
    db_session.expire_all()
    stmt = select(TrackingEvent).where(
        TrackingEvent.campaign_id == campaign_id
    )
    if event_type is not None:
        stmt = stmt.where(TrackingEvent.event_type == event_type.value)
    return list(db_session.execute(stmt).scalars())


def _launch_here(client_factory, campaign_id: str, origin: str = "http://phishsim-web:3000"):
    headers = _csrf(client_factory)
    headers["Origin"] = origin
    return client_factory.post(
        f"/api/v1/campaigns/{campaign_id}/launch", json={}, headers=headers
    )


def test_tokens_are_unguessable_unique_and_constrained(db_session):
    tokens = {tracking_service.new_token() for _ in range(500)}
    assert len(tokens) == 500
    assert all(len(token) >= 40 for token in tokens)
    constraints = {
        item["name"]
        for item in inspect(db_session.get_bind()).get_unique_constraints(
            "tracking_links"
        )
    }
    assert "uq_tracking_links_token" in constraints
    columns = {
        item["name"]
        for item in inspect(db_session.get_bind()).get_columns("tracking_events")
    }
    assert "ip" not in columns
    assert "ip_address" not in columns
    assert "user_agent" not in columns


def test_launch_creates_tokens_and_send_rows_per_target(
    db_session, client_factory, organization
):
    setup = _setup(db_session, organization)
    admin1, _admin2, _analyst, _employee, _template_row, _group_row = setup
    campaign_id, _auth_id = _approved_campaign(
        db_session, client_factory, organization, setup
    )
    login_as(client_factory, admin1.email, PASSWORD)

    launched = _launch_here(client_factory, campaign_id)
    assert launched.status_code == 200, launched.text
    assert launched.json()["campaign"]["status"] in ("scheduled", "running")

    links = _links(db_session, campaign_id)
    sends = _sends(db_session, campaign_id)
    assert len(links) == 5
    assert len({link.token for link in links}) == 5
    assert len(sends) == 5
    assert {row.status for row in sends} == {CampaignSendStatus.QUEUED.value}
    campaign = db_session.get(Campaign, campaign_id)
    assert campaign is not None
    assert campaign.tracking_base_url == "http://phishsim-web:3000"

    listing = client_factory.get(f"/api/v1/campaigns/{campaign_id}/sends")
    assert listing.status_code == 200, listing.text
    body = listing.json()["sends"]
    assert len(body) == 5
    assert {row["status"] for row in body} == {"queued"}
    assert all("token" not in row for row in body)


def test_repeat_clicks_record_once_and_invalid_token_redirects_same(
    db_session, client_factory, organization
):
    setup = _setup(db_session, organization)
    admin1, _admin2, _analyst, _employee, _template_row, _group_row = setup
    campaign_id, _auth_id = _approved_campaign(
        db_session, client_factory, organization, setup
    )
    login_as(client_factory, admin1.email, PASSWORD)
    assert _launch_here(client_factory, campaign_id).status_code == 200
    token = _links(db_session, campaign_id)[0].token

    first = client_factory.get(
        f"/t/{token}",
        headers={"user-agent": CHROME_UA},
        follow_redirects=False,
    )
    second = client_factory.get(
        f"/t/{token}",
        headers={"user-agent": CHROME_UA},
        follow_redirects=False,
    )
    assert first.status_code == 302
    assert second.status_code == 302
    assert urlsplit(first.headers["location"]).path == f"/learn/{token}"
    assert urlsplit(first.headers["location"]).path == urlsplit(
        second.headers["location"]
    ).path
    assert len(_events(db_session, campaign_id, TrackingEventType.CLICKED)) == 1

    invalid = client_factory.get(
        "/t/not-a-real-token",
        headers={"user-agent": CHROME_UA},
        follow_redirects=False,
    )
    assert invalid.status_code == 302
    assert urlsplit(invalid.headers["location"]).path == "/learn/not-a-real-token"
    assert len(_events(db_session, campaign_id, TrackingEventType.CLICKED)) == 1

    valid_api = client_factory.get(f"/api/v1/awareness/{token}")
    invalid_api = client_factory.get("/api/v1/awareness/not-a-real-token")
    assert valid_api.status_code == invalid_api.status_code == 200
    assert set(valid_api.json()) == set(invalid_api.json())
    assert valid_api.json()["simulation"] is True
    assert invalid_api.json()["simulation"] is True


def test_awareness_content_uses_template_red_flags(
    db_session, client_factory, organization
):
    setup = _setup(db_session, organization)
    admin1, _admin2, _analyst, _employee, template, _group_row = setup
    db_session.add(
        TemplateRedFlag(
            template_id=template.id,
            label="Lookalike domain",
            explanation="The domain was one character away from the real one.",
        )
    )
    db_session.commit()
    campaign_id, _auth_id = _approved_campaign(
        db_session, client_factory, organization, setup
    )
    login_as(client_factory, admin1.email, PASSWORD)
    assert _launch_here(client_factory, campaign_id).status_code == 200
    token = _links(db_session, campaign_id)[0].token

    response = client_factory.get(f"/api/v1/awareness/{token}")
    assert response.status_code == 200
    assert response.json()["red_flags"][0]["label"] == "Lookalike domain"


def test_bot_and_preview_clicks_are_not_recorded_but_still_redirect(
    db_session, client_factory, organization
):
    setup = _setup(db_session, organization)
    admin1, _admin2, _analyst, _employee, _template_row, _group_row = setup
    campaign_id, _auth_id = _approved_campaign(
        db_session, client_factory, organization, setup
    )
    login_as(client_factory, admin1.email, PASSWORD)
    assert _launch_here(client_factory, campaign_id).status_code == 200
    token = _links(db_session, campaign_id)[0].token

    for agent in (
        "Googlebot/2.1 (+http://www.google.com/bot.html)",
        "facebookexternalhit/1.1",
        "Slackbot-LinkExpanding 1.0",
    ):
        response = client_factory.get(
            f"/t/{token}",
            headers={"user-agent": agent},
            follow_redirects=False,
        )
        assert response.status_code == 302
    assert _events(db_session, campaign_id, TrackingEventType.CLICKED) == []

    human = client_factory.get(
        f"/t/{token}",
        headers={"user-agent": CHROME_UA},
        follow_redirects=False,
    )
    assert human.status_code == 302
    assert len(_events(db_session, campaign_id, TrackingEventType.CLICKED)) == 1


def test_events_store_no_raw_ip_or_user_agent(
    db_session, client_factory, organization
):
    setup = _setup(db_session, organization)
    admin1, _admin2, _analyst, _employee, _template_row, _group_row = setup
    campaign_id, _auth_id = _approved_campaign(
        db_session, client_factory, organization, setup
    )
    login_as(client_factory, admin1.email, PASSWORD)
    assert _launch_here(client_factory, campaign_id).status_code == 200
    token = _links(db_session, campaign_id)[0].token
    unique_agent = "HumanBrowser/1.0 PrivateAgentMarker"

    client_factory.get(
        f"/t/{token}",
        headers={
            "user-agent": unique_agent,
            "x-forwarded-for": "203.0.113.9",
        },
        follow_redirects=False,
    )
    events = _events(db_session, campaign_id)
    assert events
    for event in events:
        values = " ".join(str(value) for value in event.__dict__.values())
        assert "203.0.113.9" not in values
        assert "PrivateAgentMarker" not in values
        assert set(event.__dict__) == {
            "_sa_instance_state",
            "id",
            "org_id",
            "campaign_id",
            "tracking_link_id",
            "event_type",
            "occurred_at",
        }


def test_celery_task_sends_launched_messages_to_mailpit(
    db_session, client_factory, organization, monkeypatch
):
    setup = _setup(db_session, organization)
    admin1, admin2, analyst, employee, _base_template, _base_group = setup
    unique = uuid.uuid4().hex[:10]
    template = _template(
        db_session,
        organization,
        name=f"Tracking template {unique}",
        subject=f"Tracking {unique} for {{{{first_name}}}}",
        body="Hello {{first_name}}, open {{tracking_link}} to review the invoice.",
    )
    group = _group(db_session, organization, f"Tracking Group {unique}", members=5)
    setup = (admin1, admin2, analyst, employee, template, group)
    campaign_id, _auth_id = _approved_campaign(
        db_session, client_factory, organization, setup
    )
    login_as(client_factory, admin1.email, PASSWORD)
    assert _launch_here(client_factory, campaign_id).status_code == 200

    links = _links(db_session, campaign_id)
    assert len(links) == 5
    campaign = db_session.get(Campaign, campaign_id)
    assert campaign is not None
    assert campaign.send_time is not None

    monkeypatch.setattr(tasks, "SessionLocal", lambda: nullcontext(db_session))
    result = tasks.dispatch_due.run(
        str(campaign_id), now_iso=campaign.send_time.isoformat()
    )
    db_session.commit()
    assert result["sent"] == 5
    db_session.expire_all()
    rows = _sends(db_session, campaign_id)
    assert {row.status for row in rows} == {CampaignSendStatus.SENT.value}
    assert len(_events(db_session, campaign_id, TrackingEventType.DELIVERED)) == 5
    assert _events(db_session, campaign_id, TrackingEventType.CLICKED) == []

    target_emails = set(
        db_session.execute(
            select(Target.email).where(
                Target.id.in_([link.target_id for link in links])
            )
        ).scalars()
    )
    messages = []
    deadline = time.monotonic() + 15
    with httpx.Client(base_url=MAILPIT_URL, timeout=10) as client:
        while time.monotonic() < deadline:
            payload = client.get("/api/v1/messages", params={"limit": 200}).json()
            messages = [
                message
                for message in payload.get("messages", [])
                if {item.get("Address") for item in message.get("To", [])}
                & target_emails
            ]
            if len(messages) >= 5:
                break
            time.sleep(0.3)
        assert len(messages) >= 5
        first_target = db_session.get(Target, links[0].target_id)
        assert first_target is not None
        first = next(
            message
            for message in messages
            if first_target.email
            in {item.get("Address") for item in message.get("To", [])}
        )
        detail = client.get(f"/api/v1/message/{first['ID']}").json()

    html = detail.get("HTML") or detail.get("Html") or detail.get("Text") or ""
    token = links[0].token
    assert f"/t/{token}" in html

    statuses = client_factory.get(f"/api/v1/campaigns/{campaign_id}/sends")
    assert statuses.status_code == 200
    assert {row["status"] for row in statuses.json()["sends"]} == {"sent"}
    assert db_session.execute(
        select(func.count(CampaignSend.id)).where(
            CampaignSend.campaign_id == campaign_id,
            CampaignSend.failure_code.is_not(None),
        )
    ).scalar_one() == 0


def test_campaign_status_can_complete_after_delivery(
    db_session, client_factory, organization, monkeypatch
):
    setup = _setup(db_session, organization)
    campaign_id, _auth_id = _approved_campaign(
        db_session, client_factory, organization, setup
    )
    admin1 = setup[0]
    login_as(client_factory, admin1.email, PASSWORD)
    assert _launch_here(client_factory, campaign_id).status_code == 200
    campaign = db_session.get(Campaign, campaign_id)
    assert campaign is not None and campaign.send_time is not None

    monkeypatch.setattr(tasks, "SessionLocal", lambda: nullcontext(db_session))
    tasks.dispatch_due.run(
        str(campaign_id), now_iso=campaign.send_time.isoformat()
    )
    db_session.commit()
    db_session.expire_all()
    assert db_session.get(Campaign, campaign_id).status == CampaignStatus.COMPLETED
