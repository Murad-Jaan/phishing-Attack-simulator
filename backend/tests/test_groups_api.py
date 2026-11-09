"""M3 groups/targets API: RBAC, CSRF, org isolation, CRUD and audit."""

import uuid

from sqlalchemy import select

from app.core.security import hash_password
from app.models import AuditLog, Group, GroupMember, Organization, Target, User, UserRole
from tests.conftest import login_as, session_csrf_token

GROUPS = "/api/v1/groups"


def _make_user(db_session, user_factory, email: str, role: UserRole):
    user = user_factory(email=email, role=role)
    user.password_hash = hash_password("pass123456")
    db_session.commit()
    return user


def _login(db_session, client_factory, user_factory, email: str, role: UserRole) -> str:
    _make_user(db_session, user_factory, email, role)
    login_as(client_factory, email, "pass123456")
    return session_csrf_token(client_factory)


def _create_group(client, token: str, name: str = "Finance") -> dict:
    r = client.post(
        GROUPS,
        json={"name": name, "description": "Finance staff", "department": "Finance"},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 201, r.text
    return r.json()["group"]


def _create_target(client, token: str, email: str, name: str | None = "Person"):
    r = client.post(
        "/api/v1/targets",
        json={"email": email, "display_name": name},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 201, r.text
    return r.json()["target"]


def _second_org(db_session, role: UserRole = UserRole.ADMIN):
    org = Organization(
        name="Other Organization",
        slug="other-org",
        primary_domain="other.example.test",
        is_demo=False,
    )
    db_session.add(org)
    db_session.flush()
    user = User(
        org_id=org.id,
        email="other-admin@other.example.test",
        password_hash=hash_password("pass123456"),
        display_name="Other Admin",
        role=role,
        is_active=True,
        is_demo=False,
    )
    db_session.add(user)
    db_session.flush()
    group = Group(org_id=org.id, name="Other Group")
    db_session.add(group)
    db_session.flush()
    target = Target(
        org_id=org.id, email="other-target@other.example.test", display_name="Other"
    )
    db_session.add(target)
    db_session.flush()
    db_session.commit()
    return org, user, group, target


# ---------------------------------------------------------------------------
# 401 / 403
# ---------------------------------------------------------------------------


def test_groups_require_auth_401(client_factory):
    assert client_factory.get(GROUPS).status_code == 401
    assert client_factory.post(GROUPS, json={"name": "x"}).status_code == 401
    assert client_factory.get("/api/v1/targets").status_code == 401


def test_employee_forbidden_403(db_session, client_factory, user_factory):
    _make_user(db_session, user_factory, "employee-groups@example.test", UserRole.EMPLOYEE)
    login_as(client_factory, "employee-groups@example.test", "pass123456")
    assert client_factory.get(GROUPS).status_code == 403
    token = session_csrf_token(client_factory)
    r = client_factory.post(
        GROUPS, json={"name": "Nope"}, headers={"X-CSRF-Token": token}
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"
    assert client_factory.get("/api/v1/targets").status_code == 403


def test_analyst_can_create_groups_and_targets(db_session, client_factory, user_factory):
    token = _login(
        db_session, client_factory, user_factory, "analyst-groups@example.test", UserRole.ANALYST
    )
    group = _create_group(client_factory, token, "Analyst Group")
    assert group["name"] == "Analyst Group"
    target = _create_target(client_factory, token, "analyst-target@example.test")
    r = client_factory.post(
        f"{GROUPS}/{group['id']}/members",
        json={"target_id": target["id"]},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------


def test_csrf_required_on_group_writes(db_session, client_factory, user_factory):
    _make_user(db_session, user_factory, "csrf-admin@example.test", UserRole.ADMIN)
    login_as(client_factory, "csrf-admin@example.test", "pass123456")

    r = client_factory.post(GROUPS, json={"name": "No token"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "csrf_failed"
    r = client_factory.post("/api/v1/targets", json={"email": "x@example.test"})
    assert r.status_code == 403
    r = client_factory.delete(f"{GROUPS}/{uuid.uuid4()}")
    assert r.status_code == 403
    r = client_factory.patch(f"{GROUPS}/{uuid.uuid4()}", json={"name": "x"})
    assert r.status_code == 403
    r = client_factory.post(f"{GROUPS}/{uuid.uuid4()}/members", json={"email": "a@example.test"})
    assert r.status_code == 403
    r = client_factory.post(
        f"{GROUPS}/{uuid.uuid4()}/import",
        files={"file": ("t.csv", b"email\na@example.test\n", "text/csv")},
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "csrf_failed"


# ---------------------------------------------------------------------------
# CRUD + audit
# ---------------------------------------------------------------------------


def test_group_crud_and_audit_rows(db_session, client_factory, user_factory):
    token = _login(
        db_session, client_factory, user_factory, "crud-admin@example.test", UserRole.ADMIN
    )
    group = _create_group(client_factory, token, "Sales")
    gid = group["id"]

    r = client_factory.get(f"{GROUPS}/{gid}")
    assert r.status_code == 200
    assert r.json()["group"]["members"] == []

    r = client_factory.patch(
        f"{GROUPS}/{gid}",
        json={"name": "Sales EMEA", "department": "Revenue"},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 200, r.text
    assert r.json()["group"]["name"] == "Sales EMEA"
    assert r.json()["group"]["department"] == "Revenue"

    r = client_factory.delete(f"{GROUPS}/{gid}", headers={"X-CSRF-Token": token})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert client_factory.get(f"{GROUPS}/{gid}").status_code == 404

    rows = db_session.execute(select(AuditLog).order_by(AuditLog.id)).scalars().all()
    actions = [row.action for row in rows]
    assert "group.create" in actions
    assert "group.update" in actions
    assert "group.delete" in actions


def test_target_crud_and_duplicate(db_session, client_factory, user_factory):
    token = _login(
        db_session, client_factory, user_factory, "target-admin@example.test", UserRole.ADMIN
    )
    target = _create_target(client_factory, token, "dup@example.test", "First")
    r = client_factory.post(
        "/api/v1/targets",
        json={"email": "dup@example.test"},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "duplicate_target"

    r = client_factory.patch(
        f"/api/v1/targets/{target['id']}",
        json={"display_name": "Updated"},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 200, r.text
    assert r.json()["target"]["display_name"] == "Updated"

    r = client_factory.delete(
        f"/api/v1/targets/{target['id']}", headers={"X-CSRF-Token": token}
    )
    assert r.status_code == 200

    actions = [
        row.action
        for row in db_session.execute(select(AuditLog).order_by(AuditLog.id)).scalars()
    ]
    assert {"target.create", "target.update", "target.delete"}.issubset(actions)


def test_invalid_target_email_rejected(db_session, client_factory, user_factory):
    token = _login(
        db_session, client_factory, user_factory, "bad-email-admin@example.test", UserRole.ADMIN
    )
    r = client_factory.post(
        "/api/v1/targets",
        json={"email": "not-an-email"},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_error"


def test_csv_template_download(db_session, client_factory, user_factory):
    _login(
        db_session, client_factory, user_factory, "template-admin@example.test", UserRole.ADMIN
    )
    r = client_factory.get(f"{GROUPS}/import-template")
    assert r.status_code == 200
    assert r.text.startswith("email,")
    assert "attachment" in r.headers["content-disposition"]


# ---------------------------------------------------------------------------
# Membership
# ---------------------------------------------------------------------------


def test_add_and_remove_member_audited(db_session, client_factory, user_factory):
    token = _login(
        db_session, client_factory, user_factory, "member-admin@example.test", UserRole.ADMIN
    )
    group = _create_group(client_factory, token, "Ops")
    target = _create_target(client_factory, token, "member@example.test")

    r = client_factory.post(
        f"{GROUPS}/{group['id']}/members",
        json={"target_id": target["id"]},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["group"]["member_count"] == 1
    assert body["group"]["members"][0]["email"] == "member@example.test"

    r = client_factory.post(
        f"{GROUPS}/{group['id']}/members",
        json={"target_id": target["id"]},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "duplicate_member"

    r = client_factory.delete(
        f"{GROUPS}/{group['id']}/members/{target['id']}",
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 200, r.text
    assert r.json()["group"]["member_count"] == 0

    actions = [
        row.action
        for row in db_session.execute(select(AuditLog).order_by(AuditLog.id)).scalars()
    ]
    assert "group.member_add" in actions
    assert "group.member_remove" in actions


def test_add_member_by_email_creates_target(db_session, client_factory, user_factory):
    token = _login(
        db_session, client_factory, user_factory, "member-email@example.test", UserRole.ADMIN
    )
    group = _create_group(client_factory, token, "By Email")
    r = client_factory.post(
        f"{GROUPS}/{group['id']}/members",
        json={"email": "by-email@example.test", "display_name": "Created"},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 200, r.text
    assert r.json()["group"]["member_count"] == 1
    target = db_session.execute(
        select(Target).where(Target.email == "by-email@example.test")
    ).scalar_one()
    assert target.display_name == "Created"


def test_suppression_flag_follows_org_minimum(db_session, client_factory, user_factory, organization):
    organization.min_group_size = 5
    db_session.flush()
    token = _login(
        db_session, client_factory, user_factory, "suppress-admin@example.test", UserRole.ADMIN
    )
    group = _create_group(client_factory, token, "Small Team")
    for i in range(3):
        target = _create_target(client_factory, token, f"small{i}@example.test")
        r = client_factory.post(
            f"{GROUPS}/{group['id']}/members",
            json={"target_id": target["id"]},
            headers={"X-CSRF-Token": token},
        )
        assert r.status_code == 200, r.text

    r = client_factory.get(f"{GROUPS}/{group['id']}")
    assert r.status_code == 200
    body = r.json()["group"]
    assert body["member_count"] == 3
    assert body["suppressed"] is True
    assert body["min_group_size"] == 5

    for i in range(2):
        target = _create_target(client_factory, token, f"small-extra{i}@example.test")
        client_factory.post(
            f"{GROUPS}/{group['id']}/members",
            json={"target_id": target["id"]},
            headers={"X-CSRF-Token": token},
        )
    r = client_factory.get(f"{GROUPS}/{group['id']}")
    assert r.json()["group"]["suppressed"] is False


# ---------------------------------------------------------------------------
# Org isolation
# ---------------------------------------------------------------------------


def test_org_isolation_groups_and_targets(db_session, client_factory, user_factory):
    _login(
        db_session, client_factory, user_factory, "iso-admin@example.test", UserRole.ADMIN
    )
    org2, user2, group2, target2 = _second_org(db_session)

    listed = client_factory.get(GROUPS)
    assert listed.status_code == 200
    ids = [g["id"] for g in listed.json()["groups"]]
    assert str(group2.id) not in ids

    assert client_factory.get(f"{GROUPS}/{group2.id}").status_code == 404
    assert (
        client_factory.patch(
            f"{GROUPS}/{group2.id}",
            json={"name": "Hijack"},
            headers={"X-CSRF-Token": session_csrf_token(client_factory)},
        ).status_code
        == 404
    )
    assert (
        client_factory.delete(
            f"{GROUPS}/{group2.id}",
            headers={"X-CSRF-Token": session_csrf_token(client_factory)},
        ).status_code
        == 404
    )
    assert client_factory.get(f"/api/v1/targets/{target2.id}").status_code == 404
    targets = client_factory.get("/api/v1/targets").json()["targets"]
    assert str(target2.id) not in [t["id"] for t in targets]

    own_group = _create_group(client_factory, token=session_csrf_token(client_factory))
    r = client_factory.post(
        f"{GROUPS}/{own_group['id']}/members",
        json={"target_id": str(target2.id)},
        headers={"X-CSRF-Token": session_csrf_token(client_factory)},
    )
    assert r.status_code == 404
    memberships = db_session.execute(
        select(GroupMember).where(GroupMember.target_id == target2.id)
    ).scalars().all()
    assert memberships == []


def test_other_org_admin_cannot_see_first_org_data(
    db_session, client_factory, user_factory, organization
):
    target = Target(org_id=organization.id, email="org1@example.test", display_name="Org 1")
    db_session.add(target)
    db_session.commit()

    org2, user2, group2, target2 = _second_org(db_session)
    login_as(client_factory, user2.email, "pass123456")
    ids = [g["id"] for g in client_factory.get(GROUPS).json()["groups"]]
    assert ids == [str(group2.id)]
    target_ids = [t["id"] for t in client_factory.get("/api/v1/targets").json()["targets"]]
    assert target_ids == [str(target2.id)]
