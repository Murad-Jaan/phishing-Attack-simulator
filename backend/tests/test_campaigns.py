"""M5 campaigns: draft autosave, the separation-of-duties authorization gate,
scope revalidation at launch, safe Mailpit test sends, RBAC/CSRF/org isolation,
audit coverage and the single 0006 migration head."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select, text

from app.core.security import hash_password
from app.models import (
    AuditLog,
    Authorization,
    Campaign,
    CampaignStatus,
    Group,
    GroupMember,
    Organization,
    Target,
    Template,
    TemplateDifficulty,
    TemplateStatus,
    User,
    UserRole,
)
from app.services import campaign_service
from tests.conftest import login_as, session_csrf_token

PASSWORD = "pass123456"


def _make_user(
    db_session,
    organization: Organization,
    email: str,
    role: UserRole,
    *,
    display_name: str = "Test User",
) -> User:
    user = User(
        org_id=organization.id,
        email=email,
        password_hash=hash_password(PASSWORD),
        display_name=display_name,
        role=role,
        is_active=True,
        is_demo=False,
    )
    db_session.add(user)
    db_session.commit()
    return user


def _template(
    db_session,
    organization: Organization,
    *,
    name: str = "M5 campaign template",
    subject: str = "Invoice for {{first_name}}",
    body: str = "Hello {{first_name}}, open {{tracking_link}}.",
    status: TemplateStatus = TemplateStatus.PUBLISHED,
    version: int = 1,
) -> Template:
    template = Template(
        org_id=organization.id,
        family_id=uuid.uuid4(),
        version=version,
        name=name,
        sender="Billing <billing@example.test>",
        subject=subject,
        body=body,
        difficulty=TemplateDifficulty.EASY,
        attack_technique_id="T1566.002",
        lure_type="credential_harvest",
        status=status,
    )
    db_session.add(template)
    db_session.commit()
    return template


def _group(db_session, organization: Organization, name: str, members: int = 5) -> Group:
    group = Group(org_id=organization.id, name=name, description="Test group")
    db_session.add(group)
    db_session.flush()
    for index in range(members):
        target = Target(
            org_id=organization.id,
            email=f"{name.lower().replace(' ', '-')}-{index}@example.test",
            display_name=f"Target {index}",
        )
        db_session.add(target)
        db_session.flush()
        db_session.add(GroupMember(group_id=group.id, target_id=target.id))
    db_session.commit()
    return group


def _send_time(days: int = 2) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def _csrf(client) -> dict[str, str]:
    return {"X-CSRF-Token": session_csrf_token(client)}


def _create_campaign(
    client,
    *,
    template: Template,
    group: Group,
    name: str = "Q4 awareness",
    send_time: str | None = None,
    sending_domain: str = "example.test",
    csrf: bool = True,
):
    payload = {
        "name": name,
        "description": "Draft created by the test",
        "template_id": str(template.id),
        "group_id": str(group.id),
        "send_time": send_time or _send_time(),
        "sending_domain": sending_domain,
    }
    headers = _csrf(client) if csrf else {}
    return client.post("/api/v1/campaigns", json=payload, headers=headers)


def _request_auth(client, campaign_id: str, *, days: int = 2):
    send_time = datetime.now(UTC) + timedelta(days=days)
    return client.post(
        f"/api/v1/campaigns/{campaign_id}/request-authorization",
        json={
            "valid_from": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            "valid_until": (send_time + timedelta(days=1)).isoformat(),
            "note": "Please review this scope",
        },
        headers=_csrf(client),
    )


def _approve(client, authorization_id: str, *, csrf: bool = True):
    headers = _csrf(client) if csrf else {}
    return client.post(
        f"/api/v1/authorizations/{authorization_id}/approve",
        json={"note": "Approved by a second admin"},
        headers=headers,
    )


def _launch(client, campaign_id: str, *, csrf: bool = True):
    headers = _csrf(client) if csrf else {}
    return client.post(
        f"/api/v1/campaigns/{campaign_id}/launch", json={}, headers=headers
    )


def _setup(
    db_session, organization, *, group_members: int = 5
):
    admin1 = _make_user(
        db_session, organization, "m5-admin1@example.test", UserRole.ADMIN, display_name="Admin One"
    )
    admin2 = _make_user(
        db_session, organization, "m5-admin2@example.test", UserRole.ADMIN, display_name="Admin Two"
    )
    analyst = _make_user(
        db_session, organization, "m5-analyst@example.test", UserRole.ANALYST
    )
    employee = _make_user(
        db_session, organization, "m5-employee@example.test", UserRole.EMPLOYEE
    )
    template = _template(db_session, organization)
    group = _group(db_session, organization, "M5 Group", members=group_members)
    return admin1, admin2, analyst, employee, template, group


def _approved_campaign(db_session, client, organization, setup):
    admin1, admin2, _analyst, _employee, template, group = setup
    login_as(client, admin1.email, PASSWORD)
    created = _create_campaign(client, template=template, group=group)
    assert created.status_code == 201, created.text
    campaign_id = created.json()["campaign"]["id"]
    requested = _request_auth(client, campaign_id)
    assert requested.status_code == 200, requested.text
    authorization_id = requested.json()["authorization"]["id"]
    login_as(client, admin2.email, PASSWORD)
    approved = _approve(client, authorization_id)
    assert approved.status_code == 200, approved.text
    return campaign_id, authorization_id


def test_migration_0006_is_single_head_and_tables_exist(db_session):
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    backend_dir = Path(__file__).resolve().parent.parent
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    assert ScriptDirectory.from_config(config).get_heads() == [
        "0006_campaigns_authorizations"
    ]

    revision = db_session.execute(text("select version_num from alembic_version")).scalar()
    assert revision == "0006_campaigns_authorizations"
    assert db_session.execute(text("select to_regclass('campaigns')")).scalar()
    assert db_session.execute(text("select to_regclass('authorizations')")).scalar()


def test_unauthenticated_and_employee_are_denied(db_session, client_factory, organization):
    _admin1, _admin2, _analyst, employee, template, group = _setup(
        db_session, organization
    )
    assert client_factory.get("/api/v1/campaigns").status_code == 401
    assert client_factory.post("/api/v1/campaigns", json={"name": "x"}).status_code == 401

    login_as(client_factory, employee.email, PASSWORD)
    response = client_factory.get("/api/v1/campaigns")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    response = _create_campaign(client_factory, template=template, group=group)
    assert response.status_code == 403


def test_write_without_csrf_is_rejected(db_session, client_factory, organization):
    admin1, _admin2, _analyst, _employee, template, group = _setup(
        db_session, organization
    )
    login_as(client_factory, admin1.email, PASSWORD)
    response = _create_campaign(
        client_factory, template=template, group=group, csrf=False
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.ANALYST])
def test_staff_can_create_update_and_read_drafts(
    db_session, client_factory, organization, role
):
    _admin1, _admin2, analyst, _employee, template, group = _setup(
        db_session, organization
    )
    actor = analyst if role == UserRole.ANALYST else _make_user(
        db_session, organization, "m5-create-admin@example.test", UserRole.ADMIN
    )
    login_as(client_factory, actor.email, PASSWORD)

    created = _create_campaign(
        client_factory, template=template, group=group, name="Initial name"
    )
    assert created.status_code == 201, created.text
    campaign = created.json()["campaign"]
    assert campaign["status"] == "draft"
    assert campaign["template_version"] == 1
    assert campaign["target_count"] == 5

    patched = client_factory.patch(
        f"/api/v1/campaigns/{campaign['id']}",
        json={"name": "Autosaved name", "description": "Saved by autosave"},
        headers=_csrf(client_factory),
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["campaign"]["name"] == "Autosaved name"

    fetched = client_factory.get(f"/api/v1/campaigns/{campaign['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["campaign"]["description"] == "Saved by autosave"
    listed = client_factory.get("/api/v1/campaigns").json()
    assert listed["total"] == 1
    assert listed["campaigns"][0]["id"] == campaign["id"]


def test_draft_rejects_unpublished_template(db_session, client_factory, organization):
    admin1, *_rest, group = _setup(db_session, organization)
    draft_template = _template(
        db_session, organization, name="Draft only", status=TemplateStatus.DRAFT
    )
    login_as(client_factory, admin1.email, PASSWORD)
    response = _create_campaign(client_factory, template=draft_template, group=group)
    assert response.status_code == 422
    assert "template_id" in response.json()["error"]["fields"]


def test_requester_cannot_approve_their_own_request(
    db_session, client_factory, organization
):
    admin1, _admin2, _analyst, _employee, template, group = _setup(
        db_session, organization
    )
    login_as(client_factory, admin1.email, PASSWORD)
    campaign_id = _create_campaign(
        client_factory, template=template, group=group
    ).json()["campaign"]["id"]
    authorization_id = _request_auth(client_factory, campaign_id).json()[
        "authorization"
    ]["id"]

    response = _approve(client_factory, authorization_id)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "separation_of_duties"


def test_second_admin_approval_unlocks_launch(
    db_session, client_factory, organization
):
    admin1, admin2, _analyst, _employee, template, group = _setup(
        db_session, organization
    )
    login_as(client_factory, admin1.email, PASSWORD)
    campaign_id = _create_campaign(
        client_factory, template=template, group=group
    ).json()["campaign"]["id"]
    requested = _request_auth(client_factory, campaign_id)
    assert requested.status_code == 200
    assert requested.json()["campaign"]["status"] == "pending_authorization"
    authorization_id = requested.json()["authorization"]["id"]

    login_as(client_factory, admin2.email, PASSWORD)
    approved = _approve(client_factory, authorization_id)
    assert approved.status_code == 200, approved.text
    assert approved.json()["authorization"]["status"] == "approved"
    assert approved.json()["authorization"]["approved_by_email"] == admin2.email

    login_as(client_factory, admin1.email, PASSWORD)
    launched = _launch(client_factory, campaign_id)
    assert launched.status_code == 200, launched.text
    assert launched.json()["campaign"]["status"] in ("scheduled", "running")


def test_launch_without_approval_returns_missing_requirements(
    db_session, client_factory, organization
):
    admin1, _admin2, _analyst, _employee, template, group = _setup(
        db_session, organization
    )
    login_as(client_factory, admin1.email, PASSWORD)
    campaign_id = _create_campaign(
        client_factory, template=template, group=group
    ).json()["campaign"]["id"]

    response = _launch(client_factory, campaign_id)
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "authorization_required"
    assert "authorization" in error["fields"]
    assert "status" in error["fields"]


def test_expired_approval_blocks_launch(
    db_session, client_factory, organization
):
    admin1, admin2, _analyst, _employee, template, group = _setup(
        db_session, organization
    )
    login_as(client_factory, admin1.email, PASSWORD)
    campaign_id = _create_campaign(
        client_factory, template=template, group=group
    ).json()["campaign"]["id"]
    authorization_id = _request_auth(client_factory, campaign_id).json()[
        "authorization"
    ]["id"]
    login_as(client_factory, admin2.email, PASSWORD)
    assert _approve(client_factory, authorization_id).status_code == 200

    auth = db_session.get(Authorization, uuid.UUID(authorization_id))
    auth.end_date = datetime.now(UTC) - timedelta(minutes=1)
    db_session.add(auth)
    db_session.commit()

    login_as(client_factory, admin1.email, PASSWORD)
    response = _launch(client_factory, campaign_id)
    assert response.status_code == 409
    assert "expired" in response.json()["error"]["fields"]


@pytest.mark.parametrize("field", ["group_id", "template_id", "send_time"])
def test_scope_change_after_approval_revokes_it(
    db_session, client_factory, organization, field
):
    admin1, _admin2, _analyst, _employee, template, group = _setup(
        db_session, organization
    )
    other_group = _group(db_session, organization, "Other M5 Group", members=5)
    other_template = _template(db_session, organization, name="Second template")
    login_as(client_factory, admin1.email, PASSWORD)
    campaign_id = _create_campaign(
        client_factory, template=template, group=group
    ).json()["campaign"]["id"]
    authorization_id = _request_auth(client_factory, campaign_id).json()[
        "authorization"
    ]["id"]
    login_as(client_factory, "m5-admin2@example.test", PASSWORD)
    assert _approve(client_factory, authorization_id).status_code == 200

    login_as(client_factory, admin1.email, PASSWORD)
    response = client_factory.patch(
        f"/api/v1/campaigns/{campaign_id}",
        json={field: _send_time(5) if field == "send_time" else str(
            other_group.id if field == "group_id" else other_template.id
        )},
        headers=_csrf(client_factory),
    )
    assert response.status_code == 200, response.text
    assert response.json()["campaign"]["status"] == "draft"
    assert response.json()["campaign"]["authorization"]["status"] == "revoked"

    blocked = _launch(client_factory, campaign_id)
    assert blocked.status_code == 409


def test_domain_allowlist_and_minimum_group_size_are_gating(
    db_session, client_factory, organization
):
    admin1, _admin2, _analyst, _employee, template, _group5 = _setup(
        db_session, organization
    )
    too_small = _group(db_session, organization, "Tiny M5 Group", members=3)
    allowed_group = _group(db_session, organization, "Allowed M5 Group", members=5)
    login_as(client_factory, admin1.email, PASSWORD)

    small = _create_campaign(
        client_factory, template=template, group=too_small, name="Too small"
    )
    assert small.status_code == 201
    response = _request_auth(client_factory, small.json()["campaign"]["id"])
    assert response.status_code == 422
    assert "target_count" in response.json()["error"]["fields"]

    bad_domain = _create_campaign(
        client_factory,
        template=template,
        group=allowed_group,
        name="Bad domain",
        sending_domain="evil.example.com",
    )
    assert bad_domain.status_code == 201
    response = _request_auth(client_factory, bad_domain.json()["campaign"]["id"])
    assert response.status_code == 422
    assert "sending_domain" in response.json()["error"]["fields"]


def test_analyst_can_request_but_not_approve(
    db_session, client_factory, organization
):
    _admin1, _admin2, analyst, _employee, template, group = _setup(
        db_session, organization
    )
    login_as(client_factory, analyst.email, PASSWORD)
    campaign_id = _create_campaign(
        client_factory, template=template, group=group
    ).json()["campaign"]["id"]
    authorization_id = _request_auth(client_factory, campaign_id).json()[
        "authorization"
    ]["id"]

    response = _approve(client_factory, authorization_id)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert client_factory.get("/api/v1/authorizations").status_code == 403


def test_rejection_requires_reason_and_returns_campaign_to_draft(
    db_session, client_factory, organization
):
    admin1, admin2, _analyst, _employee, template, group = _setup(
        db_session, organization
    )
    login_as(client_factory, admin1.email, PASSWORD)
    campaign_id = _create_campaign(
        client_factory, template=template, group=group
    ).json()["campaign"]["id"]
    authorization_id = _request_auth(client_factory, campaign_id).json()[
        "authorization"
    ]["id"]

    login_as(client_factory, admin2.email, PASSWORD)
    missing = client_factory.post(
        f"/api/v1/authorizations/{authorization_id}/reject",
        json={"reason": "   "},
        headers=_csrf(client_factory),
    )
    assert missing.status_code == 400
    assert missing.json()["error"]["code"] == "validation_error"

    rejected = client_factory.post(
        f"/api/v1/authorizations/{authorization_id}/reject",
        json={"reason": "Scope includes the wrong department."},
        headers=_csrf(client_factory),
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["authorization"]["status"] == "rejected"
    assert rejected.json()["authorization"]["reason"].startswith("Scope includes")

    login_as(client_factory, admin1.email, PASSWORD)
    campaign = client_factory.get(f"/api/v1/campaigns/{campaign_id}").json()[
        "campaign"
    ]
    assert campaign["status"] == "draft"


def test_pause_and_cancel_are_audited(
    db_session, client_factory, organization
):
    admin1, admin2, _analyst, employee, template, group = _setup(
        db_session, organization
    )
    login_as(client_factory, admin1.email, PASSWORD)
    campaign_id = _create_campaign(
        client_factory, template=template, group=group
    ).json()["campaign"]["id"]
    authorization_id = _request_auth(client_factory, campaign_id).json()[
        "authorization"
    ]["id"]
    login_as(client_factory, admin2.email, PASSWORD)
    assert _approve(client_factory, authorization_id).status_code == 200

    login_as(client_factory, admin1.email, PASSWORD)
    assert _launch(client_factory, campaign_id).status_code == 200
    paused = client_factory.post(
        f"/api/v1/campaigns/{campaign_id}/pause", json={}, headers=_csrf(client_factory)
    )
    assert paused.status_code == 200
    assert paused.json()["campaign"]["status"] == "paused"
    cancelled = client_factory.post(
        f"/api/v1/campaigns/{campaign_id}/cancel", json={}, headers=_csrf(client_factory)
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["campaign"]["status"] == "cancelled"
    assert cancelled.json()["campaign"]["authorization"]["status"] == "revoked"

    actions = set(
        db_session.execute(select(AuditLog.action)).scalars()
    )
    assert {"campaign.pause", "campaign.cancel"} <= actions


def test_test_send_uses_only_sandbox_and_leaves_group_untouched(
    db_session, client_factory, organization, monkeypatch
):
    admin1, _admin2, _analyst, _employee, template, group = _setup(
        db_session, organization
    )
    captured: dict[str, str] = {}

    def fake_send(to_email: str, subject: str, body: str) -> bool:
        captured.update({"to": to_email, "subject": subject, "body": body})
        return True

    monkeypatch.setattr(campaign_service.mail, "send_mail_sandbox", fake_send)
    login_as(client_factory, admin1.email, PASSWORD)
    campaign_id = _create_campaign(
        client_factory, template=template, group=group
    ).json()["campaign"]["id"]

    response = client_factory.post(
        f"/api/v1/campaigns/{campaign_id}/test-send",
        json={"recipient": "sandbox@example.test"},
        headers=_csrf(client_factory),
    )
    assert response.status_code == 200, response.text
    assert response.json()["recipient"] == "sandbox@example.test"
    assert captured["to"] == "sandbox@example.test"
    assert captured["subject"].startswith("[TEST]")
    assert "NOT A REAL PHISHING SIMULATION" in captured["body"]
    assert "Simulation notice" in captured["body"]
    assert campaign_service.DEFAULT_TRACKING_LINK in captured["body"]
    assert "{{tracking_link}}" not in captured["body"]
    group_emails = set(
        db_session.execute(
            select(Target.email).join(GroupMember, GroupMember.target_id == Target.id)
        ).scalars()
    )
    assert captured["to"] not in group_emails

    blocked = client_factory.post(
        f"/api/v1/campaigns/{campaign_id}/test-send",
        json={"recipient": sorted(group_emails)[0]},
        headers=_csrf(client_factory),
    )
    assert blocked.status_code == 422
    assert "recipient" in blocked.json()["error"]["fields"]


def test_test_send_arrives_in_mailpit_with_no_group_recipients(
    db_session, client_factory, organization, monkeypatch
):
    admin1, _admin2, _analyst, _employee, _template1, group = _setup(
        db_session, organization
    )
    token = f"m5-mailpit-{uuid.uuid4().hex[:8]}"
    template = _template(
        db_session,
        organization,
        name=f"Mailpit {token}",
        subject=f"Mailpit check {token}",
        body="Hello {{first_name}}, open {{tracking_link}}.",
    )
    login_as(client_factory, admin1.email, PASSWORD)
    campaign_id = _create_campaign(
        client_factory, template=template, group=group, name=f"Campaign {token}"
    ).json()["campaign"]["id"]

    response = client_factory.post(
        f"/api/v1/campaigns/{campaign_id}/test-send",
        json={"recipient": "sandbox@example.test"},
        headers=_csrf(client_factory),
    )
    assert response.status_code == 200, response.text

    message = None
    for _ in range(20):
        try:
            data = httpx.get(
                "http://mailpit:8025/api/v1/messages", timeout=5
            ).json()
        except Exception:
            time.sleep(0.25)
            continue
        messages = data.get("messages", []) if isinstance(data, dict) else data
        for item in messages:
            subject = item.get("Subject") or item.get("subject") or ""
            if token in subject:
                message = item
                break
        if message:
            break
        time.sleep(0.25)
    assert message is not None, "test message did not arrive in Mailpit"
    recipients = {
        entry.get("Address") or entry.get("address")
        for entry in (message.get("To") or [])
    }
    assert recipients == {"sandbox@example.test"}
    group_emails = set(
        db_session.execute(
            select(Target.email).join(GroupMember, GroupMember.target_id == Target.id)
        ).scalars()
    )
    assert not (recipients & group_emails)


def test_org_isolation_and_admin_authorization_list(
    db_session, client_factory, organization, user_factory
):
    admin1, admin2, _analyst, _employee, template, group = _setup(
        db_session, organization
    )
    other_org = Organization(
        name="Other Org",
        slug="m5-other-org",
        primary_domain="other.test",
    )
    db_session.add(other_org)
    db_session.flush()
    other_admin = User(
        org_id=other_org.id,
        email="m5-other-admin@example.test",
        password_hash=hash_password(PASSWORD),
        display_name="Other Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )
    other_group = Group(org_id=other_org.id, name="Other Group")
    other_template = Template(
        org_id=other_org.id,
        family_id=uuid.uuid4(),
        version=1,
        name="Other template",
        sender="Other <other@other.test>",
        subject="Other",
        body="Other",
        difficulty=TemplateDifficulty.EASY,
        attack_technique_id="none",
        lure_type="benign_control",
        status=TemplateStatus.PUBLISHED,
    )
    db_session.add_all([other_admin, other_group, other_template])
    db_session.flush()
    other_campaign = Campaign(
        org_id=other_org.id,
        name="Other campaign",
        template_id=other_template.id,
        template_version=1,
        group_id=other_group.id,
        send_time=datetime.now(UTC) + timedelta(days=1),
        sending_domain="other.test",
        status=CampaignStatus.DRAFT,
        created_by=other_admin.id,
    )
    db_session.add(other_campaign)
    db_session.commit()

    login_as(client_factory, admin1.email, PASSWORD)
    assert (
        client_factory.get(f"/api/v1/campaigns/{other_campaign.id}").status_code
        == 404
    )
    campaign_id = _create_campaign(
        client_factory, template=template, group=group
    ).json()["campaign"]["id"]
    authorization_id = _request_auth(client_factory, campaign_id).json()[
        "authorization"
    ]["id"]

    login_as(client_factory, admin2.email, PASSWORD)
    listing = client_factory.get("/api/v1/authorizations?status=requested")
    assert listing.status_code == 200
    ids = {row["id"] for row in listing.json()["authorizations"]}
    assert authorization_id in ids
    assert all(row["campaign_id"] != str(other_campaign.id) for row in listing.json()["authorizations"])

    login_as(client_factory, other_admin.email, PASSWORD)
    assert (
        client_factory.post(
            f"/api/v1/authorizations/{authorization_id}/approve",
            json={},
            headers=_csrf(client_factory),
        ).status_code
        == 404
    )


def test_approval_and_launch_require_csrf(
    db_session, client_factory, organization
):
    admin1, admin2, _analyst, _employee, template, group = _setup(
        db_session, organization
    )
    login_as(client_factory, admin1.email, PASSWORD)
    campaign_id = _create_campaign(
        client_factory, template=template, group=group
    ).json()["campaign"]["id"]
    authorization_id = _request_auth(client_factory, campaign_id).json()[
        "authorization"
    ]["id"]

    login_as(client_factory, admin2.email, PASSWORD)
    response = _approve(client_factory, authorization_id, csrf=False)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"

    login_as(client_factory, "m5-admin1@example.test", PASSWORD)
    response = _launch(client_factory, campaign_id, csrf=False)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


def test_audit_trail_covers_campaign_lifecycle(
    db_session, client_factory, organization, monkeypatch
):
    admin1, admin2, _analyst, _employee, template, group = _setup(
        db_session, organization
    )
    monkeypatch.setattr(
        campaign_service.mail, "send_mail_sandbox", lambda *args, **kwargs: True
    )
    login_as(client_factory, admin1.email, PASSWORD)
    campaign_id = _create_campaign(
        client_factory, template=template, group=group
    ).json()["campaign"]["id"]
    client_factory.patch(
        f"/api/v1/campaigns/{campaign_id}",
        json={"description": "Autosaved"},
        headers=_csrf(client_factory),
    )
    client_factory.post(
        f"/api/v1/campaigns/{campaign_id}/test-send",
        json={},
        headers=_csrf(client_factory),
    )
    authorization_id = _request_auth(client_factory, campaign_id).json()[
        "authorization"
    ]["id"]
    login_as(client_factory, admin2.email, PASSWORD)
    assert _approve(client_factory, authorization_id).status_code == 200
    login_as(client_factory, admin1.email, PASSWORD)
    assert _launch(client_factory, campaign_id).status_code == 200

    actions = set(db_session.execute(select(AuditLog.action)).scalars())
    assert {
        "campaign.create",
        "campaign.update",
        "campaign.test_send",
        "campaign.request_authorization",
        "authorization.approve",
        "campaign.launch",
    } <= actions
    rows = list(
        db_session.execute(
            select(AuditLog).where(AuditLog.entity_type == "campaign")
        ).scalars()
    )
    assert rows
    for row in rows:
        payload = f"{row.before}{row.after}"
        for email in (
            "m5-group-0@example.test",
            "m5-group-1@example.test",
        ):
            assert email not in payload
