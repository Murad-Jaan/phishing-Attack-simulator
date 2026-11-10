"""M4 template library: RBAC, CSRF, org isolation, versioning, validation,
safe preview rendering, audit rows and dev seeding."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from app.core.security import hash_password
from app.models import AuditLog, Organization, Template, TemplateDifficulty, TemplateStatus, User, UserRole
from app.scripts.seed_templates import SCENARIOS, seed_templates
from app.services import template_service
from app.services.template_service import domain_is_sandbox
from tests.conftest import login_as, session_csrf_token


def _make_user(db_session, user_factory, email: str, role: UserRole, org: Organization | None = None):
    if org is None:
        user = user_factory(email=email, role=role)
    else:
        user = User(
            org_id=org.id,
            email=email,
            password_hash=hash_password("pass123456"),
            display_name="Test User",
            role=role,
            is_active=True,
            is_demo=False,
        )
        db_session.add(user)
        db_session.flush()
    user.password_hash = hash_password("pass123456")
    db_session.commit()
    return user


def _payload(**overrides):
    data = {
        "name": "Fictional invoice reminder",
        "sender": "Billing Team <billing@vendor.example.test>",
        "subject": "Invoice ready for {{first_name}}",
        "body": "Hello {{first_name}},\n\nOpen {{tracking_link}} to review your invoice.",
        "difficulty": "easy",
        "attack_technique_id": "T1566.002",
        "lure_type": "credential_harvest",
        "status": "draft",
        "red_flags": [
            {"label": "Urgency", "explanation": "A short deadline is used."},
        ],
    }
    data.update(overrides)
    return data


def _post(client, url: str, payload: dict | None = None, *, csrf: bool = True):
    headers = {"X-CSRF-Token": session_csrf_token(client)} if csrf else {}
    return client.post(url, json=payload, headers=headers)


def _patch(client, url: str, payload: dict, *, csrf: bool = True):
    headers = {"X-CSRF-Token": session_csrf_token(client)} if csrf else {}
    return client.patch(url, json=payload, headers=headers)


def _insert_template(
    db_session,
    organization,
    *,
    name: str = "Manual template",
    subject: str = "Subject",
    body: str = "Body",
    difficulty: TemplateDifficulty = TemplateDifficulty.EASY,
    technique: str = "T1566.002",
    status: TemplateStatus = TemplateStatus.PUBLISHED,
    family_id: uuid.UUID | None = None,
    version: int = 1,
) -> Template:
    template = Template(
        org_id=organization.id,
        family_id=family_id or uuid.uuid4(),
        version=version,
        name=name,
        sender="Sender <sender@example.test>",
        subject=subject,
        body=body,
        difficulty=difficulty,
        attack_technique_id=technique,
        lure_type="test_lure",
        status=status,
    )
    db_session.add(template)
    db_session.flush()
    return template


def test_templates_unauthenticated_401(client_factory):
    assert client_factory.get("/templates").status_code == 401
    assert client_factory.get("/api/v1/templates").status_code == 401
    assert client_factory.get("/templates/anything").status_code == 401
    assert client_factory.get("/templates/anything/preview").status_code == 401
    r = client_factory.post("/api/v1/templates", json=_payload())
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"


def test_employee_403_on_read_and_write(db_session, client_factory, user_factory):
    _make_user(db_session, user_factory, "employee-tpl@example.test", UserRole.EMPLOYEE)
    login_as(client_factory, "employee-tpl@example.test", "pass123456")

    assert client_factory.get("/api/v1/templates").status_code == 403
    assert client_factory.get("/api/v1/templates").json()["error"]["code"] == "forbidden"

    r = client_factory.post("/api/v1/templates", json=_payload())
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.ANALYST])
def test_admin_and_analyst_can_list_and_create(db_session, client_factory, user_factory, role):
    _make_user(db_session, user_factory, f"author-{role.value}@example.test", role)
    login_as(client_factory, f"author-{role.value}@example.test", "pass123456")

    assert client_factory.get("/api/v1/templates").status_code == 200
    r = _post(client_factory, "/api/v1/templates", _payload())
    assert r.status_code == 201, r.text
    body = r.json()["template"]
    assert body["name"] == "Fictional invoice reminder"
    assert body["version"] == 1
    assert body["status"] == "draft"
    assert body["red_flag_count"] == 1
    assert body["red_flags"][0]["label"] == "Urgency"


def test_write_without_csrf_is_403(db_session, client_factory, user_factory):
    _make_user(db_session, user_factory, "no-csrf-tpl@example.test", UserRole.ANALYST)
    login_as(client_factory, "no-csrf-tpl@example.test", "pass123456")

    r = _post(client_factory, "/api/v1/templates", _payload(), csrf=False)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "csrf_failed"


def test_versioning_published_edit_creates_new_version(
    db_session, client_factory, user_factory
):
    _make_user(db_session, user_factory, "version-tpl@example.test", UserRole.ANALYST)
    login_as(client_factory, "version-tpl@example.test", "pass123456")

    created = _post(
        client_factory,
        "/api/v1/templates",
        _payload(status="published", subject="Original subject"),
    )
    assert created.status_code == 201, created.text
    original = created.json()["template"]

    edited = _patch(
        client_factory,
        f"/api/v1/templates/{original['id']}",
        {"subject": "Updated subject"},
    )
    assert edited.status_code == 200, edited.text
    updated = edited.json()["template"]
    assert updated["version"] == 2
    assert updated["family_id"] == original["family_id"]
    assert updated["status"] == "draft"
    assert updated["subject"] == "Updated subject"
    assert updated["id"] != original["id"]

    old = client_factory.get(f"/api/v1/templates/{original['id']}").json()["template"]
    assert old["version"] == 1
    assert old["subject"] == "Original subject"
    assert old["status"] == "published"

    listed = client_factory.get("/api/v1/templates").json()
    assert listed["total"] == 1
    assert listed["templates"][0]["id"] == updated["id"]

    draft_edit = _patch(
        client_factory,
        f"/api/v1/templates/{updated['id']}",
        {"subject": "Draft subject"},
    )
    assert draft_edit.status_code == 200
    assert draft_edit.json()["template"]["version"] == 2


def test_duplicate_creates_new_family_and_copies_red_flags(
    db_session, client_factory, user_factory
):
    _make_user(db_session, user_factory, "dup-tpl@example.test", UserRole.ADMIN)
    login_as(client_factory, "dup-tpl@example.test", "pass123456")

    created = _post(client_factory, "/api/v1/templates", _payload()).json()["template"]
    r = _post(
        client_factory,
        f"/api/v1/templates/{created['id']}/duplicate",
        {"name": "Fictional invoice reminder copy"},
    )
    assert r.status_code == 201, r.text
    copy = r.json()["template"]
    assert copy["id"] != created["id"]
    assert copy["family_id"] != created["family_id"]
    assert copy["version"] == 1
    assert copy["status"] == "draft"
    assert copy["name"] == "Fictional invoice reminder copy"
    assert copy["red_flag_count"] == created["red_flag_count"]

    action = db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "template.duplicate",
            AuditLog.entity_id == copy["id"],
        )
    ).scalar_one()
    assert action.org_id is not None


def test_archive_is_read_only_and_audited(db_session, client_factory, user_factory):
    _make_user(db_session, user_factory, "archive-tpl@example.test", UserRole.ADMIN)
    login_as(client_factory, "archive-tpl@example.test", "pass123456")

    created = _post(
        client_factory, "/api/v1/templates", _payload(status="published")
    ).json()["template"]
    archived = _post(
        client_factory, f"/api/v1/templates/{created['id']}/archive"
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["template"]["status"] == "archived"

    blocked = _patch(
        client_factory,
        f"/api/v1/templates/{created['id']}",
        {"subject": "Should not save"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "archived_read_only"

    row = db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "template.archive",
            AuditLog.entity_id == created["id"],
        )
    ).scalar_one()
    assert row.after["status"] == "archived"


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"subject": "PayPal account review"}, "subject"),
        ({"name": "Microsoft sign-in"}, "name"),
        ({"sender": "support@paypal.example.test"}, "sender"),
        ({"sender": "alerts@evil.example.org"}, "sender"),
        (
            {"body": "Hello {{first_name}}, open https://evil.example.org/login now."},
            "body",
        ),
        (
            {
                "body": (
                    "Hello {{first_name}}, <form><input type=\"password\" "
                    "name=\"password\"></form>"
                )
            },
            "body",
        ),
        ({"body": "Hello {{last_name}}"}, "body"),
        ({"attack_technique_id": "TXXXX"}, "attack_technique_id"),
        ({"difficulty": "extreme"}, "difficulty"),
        ({"status": "live"}, "status"),
        ({"red_flags": [{"label": "", "explanation": "empty"}]}, "red_flags.0.label"),
    ],
)
def test_content_validation_rejects_unsafe_values(
    db_session, client_factory, user_factory, overrides, field
):
    user = _make_user(
        db_session, user_factory, f"valid-{uuid.uuid4().hex}@example.test", UserRole.ANALYST
    )
    login_as(client_factory, user.email, "pass123456")

    r = _post(client_factory, "/api/v1/templates", _payload(**overrides))
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "validation_error"
    assert field in r.json()["error"]["fields"]


def test_preview_escapes_script_and_markup(db_session, client_factory, user_factory, organization):
    _make_user(db_session, user_factory, "preview-tpl@example.test", UserRole.ANALYST)
    login_as(client_factory, "preview-tpl@example.test", "pass123456")

    template = _insert_template(
        db_session,
        organization,
        name="<img src=x onerror=alert(1)>",
        subject="<script>alert('subject')</script>",
        body=(
            "Hello <script>alert(1)</script> "
            '<img src="https://evil.example.org/pixel.png"> '
            "<b>bold</b>"
        ),
    )
    db_session.commit()

    r = client_factory.get(f"/api/v1/templates/{template.id}/preview")
    assert r.status_code == 200, r.text
    html = r.json()["preview"]["html"]
    lowered = html.lower()
    assert "<script" not in lowered
    assert "<img" not in lowered
    assert "<b>bold</b>" not in lowered
    assert "&lt;script&gt;" in lowered
    assert "&lt;img" in lowered
    assert "&lt;b&gt;bold&lt;/b&gt;" in lowered


def test_preview_replaces_only_sandbox_placeholders(
    db_session, client_factory, user_factory
):
    _make_user(db_session, user_factory, "preview-fill@example.test", UserRole.ANALYST)
    login_as(client_factory, "preview-fill@example.test", "pass123456")

    created = _post(
        client_factory,
        "/api/v1/templates",
        _payload(
            body=(
                "Hello {{first_name}}, open {{ tracking_link }} or "
                "https://help.example.test/page"
            )
        ),
    )
    assert created.status_code == 201, created.text
    r = client_factory.get(
        f"/api/v1/templates/{created.json()['template']['id']}/preview"
    )
    html = r.json()["preview"]["html"]
    assert "Alex" in html
    assert "https://tracking.example.test/c/abc123" in html
    assert "{{" not in html


def test_org_isolation_and_404(db_session, client_factory, user_factory, organization):
    _make_user(db_session, user_factory, "org-one-tpl@example.test", UserRole.ADMIN)
    other_org = Organization(
        name="Other Organization", slug="other-org", primary_domain="other.example.test"
    )
    db_session.add(other_org)
    db_session.flush()
    other_template = _insert_template(
        db_session, other_org, name="Other org template", subject="Secret"
    )
    db_session.commit()

    login_as(client_factory, "org-one-tpl@example.test", "pass123456")
    listed = client_factory.get("/api/v1/templates").json()
    assert listed["total"] == 0
    assert all(item["name"] != "Other org template" for item in listed["templates"])

    r = client_factory.get(f"/api/v1/templates/{other_template.id}")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
    assert client_factory.get(
        f"/api/v1/templates/{other_template.id}/preview"
    ).status_code == 404


def test_list_search_and_filters(db_session, client_factory, user_factory, organization):
    _make_user(db_session, user_factory, "filters-tpl@example.test", UserRole.ANALYST)
    alpha = _insert_template(
        db_session,
        organization,
        name="Alpha invoice",
        subject="Invoice reminder",
        difficulty=TemplateDifficulty.EASY,
        technique="T1566.002",
        status=TemplateStatus.PUBLISHED,
    )
    beta = _insert_template(
        db_session,
        organization,
        name="Beta payroll",
        subject="Payroll update",
        difficulty=TemplateDifficulty.MEDIUM,
        technique="T1598",
        status=TemplateStatus.DRAFT,
    )
    _insert_template(
        db_session,
        organization,
        name="Gamma attachment",
        subject="Attachment",
        difficulty=TemplateDifficulty.HARD,
        technique="T1566.001",
        status=TemplateStatus.PUBLISHED,
    )
    db_session.commit()

    login_as(client_factory, "filters-tpl@example.test", "pass123456")

    def names(query: str) -> list[str]:
        response = client_factory.get(f"/api/v1/templates?{query}")
        assert response.status_code == 200, response.text
        return sorted(item["name"] for item in response.json()["templates"])

    assert names("search=Payroll") == [beta.name]
    assert names("difficulty=medium") == [beta.name]
    assert names("technique=T1566.002") == [alpha.name]
    assert names("status=draft") == [beta.name]
    assert names("status=published") == sorted([alpha.name, "Gamma attachment"])


def test_create_update_duplicate_archive_write_audit_rows(
    db_session, client_factory, user_factory
):
    _make_user(db_session, user_factory, "audit-tpl@example.test", UserRole.ADMIN)
    login_as(client_factory, "audit-tpl@example.test", "pass123456")

    created = _post(client_factory, "/api/v1/templates", _payload())
    template_id = created.json()["template"]["id"]
    _patch(client_factory, f"/api/v1/templates/{template_id}", {"subject": "Second"})
    _post(client_factory, f"/api/v1/templates/{template_id}/duplicate", {})
    _post(client_factory, f"/api/v1/templates/{template_id}/archive")

    actions = set(
        db_session.execute(
            select(AuditLog.action).where(
                AuditLog.entity_type == "template",
                AuditLog.actor_user_id.is_not(None),
            )
        ).scalars()
    )
    assert {
        "template.create",
        "template.update",
        "template.duplicate",
        "template.archive",
    }.issubset(actions)

    rows = list(
        db_session.execute(
            select(AuditLog).where(AuditLog.entity_type == "template")
        ).scalars()
    )
    assert rows
    for row in rows:
        assert row.org_id is not None
        blob = str({"before": row.before, "after": row.after}).lower()
        assert "password" not in blob
        assert "token" not in blob


def test_seed_templates_creates_sc_01_to_sc_10_and_is_idempotent(
    db_session, organization
):
    inserted = seed_templates(db_session, organization)
    assert inserted == 10
    db_session.commit()

    templates = list(
        db_session.execute(
            select(Template).where(
                Template.org_id == organization.id, Template.is_demo.is_(True)
            )
        ).scalars()
    )
    assert len(templates) == 10
    names = sorted(template.name for template in templates)
    assert names == sorted(scenario["name"] for scenario in SCENARIOS)
    assert names[0].startswith("SC-01")
    assert names[-1].startswith("SC-10")

    for template in templates:
        assert domain_is_sandbox(template.sender.split("@")[-1].rstrip(">"))
        assert template.is_demo is True
        assert template.status == TemplateStatus.PUBLISHED
        assert template.attack_technique_id
        assert template.difficulty in (
            TemplateDifficulty.EASY,
            TemplateDifficulty.MEDIUM,
            TemplateDifficulty.HARD,
        )
    phishing = [t for t in templates if t.attack_technique_id != "none"]
    assert len(phishing) == 7
    assert all(len(t.red_flags) >= 1 for t in phishing)

    assert seed_templates(db_session, organization) == 0
    db_session.commit()
    assert (
        db_session.execute(
            select(func.count(Template.id)).where(
                Template.org_id == organization.id, Template.is_demo.is_(True)
            )
        ).scalar_one()
        == 10
    )


def test_every_seeded_scenario_passes_content_validation():
    for scenario in SCENARIOS:
        template_service.validate_template_content(
            {
                "name": scenario["name"],
                "sender": scenario["sender"],
                "subject": scenario["subject"],
                "body": scenario["body"],
                "difficulty": scenario["difficulty"].value,
                "attack_technique_id": scenario["attack_technique_id"],
                "lure_type": scenario["lure_type"],
                "status": "published",
                "red_flags": [
                    {"label": label, "explanation": explanation}
                    for label, explanation in scenario["red_flags"]
                ],
            }
        )


def test_template_tables_and_enums_exist(db_session):
    from sqlalchemy import text

    tables = set(
        db_session.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
        ).scalars()
    )
    assert {"templates", "template_red_flags"}.issubset(tables)
    enums = set(
        db_session.execute(
            text(
                "SELECT typname FROM pg_type WHERE typname IN "
                "('template_difficulty', 'template_status')"
            )
        ).scalars()
    )
    assert enums == {"template_difficulty", "template_status"}
