"""M3 CSV import: valid, row errors, duplicates, oversize, formula injection."""

import uuid

from sqlalchemy import select

from app.core.security import hash_password
from app.models import AuditLog, Target, UserRole
from app.services import groups_service
from tests.conftest import login_as, session_csrf_token

GROUPS = "/api/v1/groups"


def _login(db_session, client_factory, user_factory, email: str | None = None) -> str:
    email = email or f"csv-{uuid.uuid4().hex[:8]}@example.test"
    user = user_factory(email=email, role=UserRole.ADMIN)
    user.password_hash = hash_password("pass123456")
    db_session.commit()
    login_as(client_factory, email, "pass123456")
    return session_csrf_token(client_factory)


def _group(client, token: str, name: str = "Import Group") -> dict:
    r = client.post(GROUPS, json={"name": name}, headers={"X-CSRF-Token": token})
    assert r.status_code == 201, r.text
    return r.json()["group"]


def _import(client, token: str, group_id: str, body: bytes, filename: str = "targets.csv"):
    return client.post(
        f"{GROUPS}/{group_id}/import",
        files={"file": (filename, body, "text/csv")},
        headers={"X-CSRF-Token": token},
    )


def test_valid_csv_import_creates_targets_and_members(
    db_session, client_factory, user_factory
):
    token = _login(db_session, client_factory, user_factory)
    group = _group(client_factory, token)
    csv_body = (
        b"email,display_name\n"
        b"alice@example.test,Alice\n"
        b"bob@example.test,Bob\n"
    )
    r = _import(client_factory, token, group["id"], csv_body)
    assert r.status_code == 200, r.text
    result = r.json()["result"]
    assert result["imported"] == 2
    assert result["skipped"] == 0
    assert result["errors"] == []
    assert r.json()["group"]["member_count"] == 2

    emails = set(
        db_session.execute(select(Target.email).where(Target.org_id == group["org_id"])).scalars()
    )
    assert {"alice@example.test", "bob@example.test"}.issubset(emails)


def test_bad_email_is_row_level_and_partial_import_keeps_valid_rows(
    db_session, client_factory, user_factory
):
    token = _login(db_session, client_factory, user_factory)
    group = _group(client_factory, token)
    csv_body = (
        b"email,display_name\n"
        b"good1@example.test,Good One\n"
        b"not-an-email,Bad Row\n"
        b"good2@example.test,Good Two\n"
    )
    r = _import(client_factory, token, group["id"], csv_body)
    assert r.status_code == 200, r.text
    result = r.json()["result"]
    assert result["imported"] == 2
    assert result["skipped"] == 1
    assert result["errors"][0]["row"] == 3
    assert result["errors"][0]["line"] == "Row 3: invalid email"
    assert r.json()["group"]["member_count"] == 2


def test_duplicate_email_within_csv_is_reported(db_session, client_factory, user_factory):
    token = _login(db_session, client_factory, user_factory)
    group = _group(client_factory, token)
    csv_body = (
        b"email,display_name\n"
        b"dupe@example.test,First\n"
        b"dupe@example.test,Second\n"
    )
    r = _import(client_factory, token, group["id"], csv_body)
    assert r.status_code == 200, r.text
    result = r.json()["result"]
    assert result["imported"] == 1
    assert result["skipped"] == 1
    assert result["errors"][0]["message"] == "duplicate email"


def test_duplicate_existing_member_is_skipped(db_session, client_factory, user_factory):
    token = _login(db_session, client_factory, user_factory)
    group = _group(client_factory, token)
    csv_body = b"email\nalready@example.test\n"
    assert _import(client_factory, token, group["id"], csv_body).status_code == 200
    r = _import(client_factory, token, group["id"], csv_body)
    assert r.status_code == 200, r.text
    result = r.json()["result"]
    assert result["imported"] == 0
    assert result["skipped"] == 1
    assert result["errors"][0]["message"] == "duplicate email"


def test_existing_org_target_is_reused_across_groups(
    db_session, client_factory, user_factory
):
    token = _login(db_session, client_factory, user_factory)
    first = _group(client_factory, token, "First Group")
    second = _group(client_factory, token, "Second Group")
    csv_body = b"email,display_name\nreuse@example.test,Reuse Person\n"
    assert _import(client_factory, token, first["id"], csv_body).status_code == 200
    r = _import(client_factory, token, second["id"], csv_body)
    assert r.status_code == 200, r.text
    assert r.json()["result"]["imported"] == 1
    targets = db_session.execute(
        select(Target).where(Target.email == "reuse@example.test")
    ).scalars().all()
    assert len(targets) == 1


def test_formula_injection_cells_are_rejected(db_session, client_factory, user_factory):
    token = _login(db_session, client_factory, user_factory)
    group = _group(client_factory, token)
    csv_body = (
        b"email,display_name\n"
        b"safe@example.test,Safe\n"
        b"=cmd@example.test,Equals\n"
        b"plus@example.test,+Plus\n"
        b"minus@example.test,-Minus\n"
        b"at@example.test,@At\n"
    )
    r = _import(client_factory, token, group["id"], csv_body)
    assert r.status_code == 200, r.text
    result = r.json()["result"]
    assert result["imported"] == 1
    assert result["skipped"] == 4
    for error in result["errors"]:
        assert error["message"] == "formula injection blocked"
    stored = db_session.execute(
        select(Target.email).where(Target.org_id == group["org_id"])
    ).scalars().all()
    assert stored == ["safe@example.test"]


def test_formula_injection_in_display_name_is_rejected(
    db_session, client_factory, user_factory
):
    token = _login(db_session, client_factory, user_factory)
    group = _group(client_factory, token)
    r = _import(
        client_factory,
        token,
        group["id"],
        b"email,display_name\nperson@example.test,=HYPERLINK(\"http://evil\")\n",
    )
    assert r.status_code == 200, r.text
    assert r.json()["result"]["imported"] == 0
    assert r.json()["result"]["errors"][0]["message"] == "formula injection blocked"
    assert (
        db_session.execute(select(Target).where(Target.email == "person@example.test"))
        .scalar_one_or_none()
        is None
    )


def test_missing_email_header_is_file_level_error(
    db_session, client_factory, user_factory
):
    token = _login(db_session, client_factory, user_factory)
    group = _group(client_factory, token)
    r = _import(client_factory, token, group["id"], b"name,department\nAlice,Finance\n")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
    assert "email column" in r.json()["error"]["message"]


def test_empty_csv_is_file_level_error(db_session, client_factory, user_factory):
    token = _login(db_session, client_factory, user_factory)
    group = _group(client_factory, token)
    r = _import(client_factory, token, group["id"], b"")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_oversize_csv_rejected_413(db_session, client_factory, user_factory):
    token = _login(db_session, client_factory, user_factory)
    group = _group(client_factory, token)
    body = b"email\n" + (b"a@example.test\n" * (groups_service.CSV_MAX_BYTES // 15 + 10))
    assert len(body) > groups_service.CSV_MAX_BYTES
    r = _import(client_factory, token, group["id"], body)
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "file_too_large"


def test_import_audit_contains_counts_only(db_session, client_factory, user_factory):
    token = _login(db_session, client_factory, user_factory)
    group = _group(client_factory, token)
    csv_body = (
        b"email,display_name\n"
        b"audit-one@example.test,One\n"
        b"bad-email,Two\n"
    )
    r = _import(client_factory, token, group["id"], csv_body)
    assert r.status_code == 200, r.text

    row = db_session.execute(
        select(AuditLog).where(AuditLog.action == "group.import").order_by(AuditLog.id.desc())
    ).scalars().first()
    assert row is not None
    assert row.entity_type == "group"
    assert row.entity_id == group["id"]
    assert row.after == {
        "imported": 1,
        "skipped": 1,
        "total": 2,
        "errors": 1,
    }
    serialized = str(row.after) + str(row.before) + str(row.reason)
    assert "audit-one@example.test" not in serialized
    assert "bad-email" not in serialized


def test_import_requires_csrf_and_staff(db_session, client_factory, user_factory):
    token = _login(db_session, client_factory, user_factory)
    group = _group(client_factory, token)
    r = client_factory.post(
        f"{GROUPS}/{group['id']}/import",
        files={"file": ("t.csv", b"email\na@example.test\n", "text/csv")},
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "csrf_failed"

    employee = user_factory(email="csv-employee@example.test", role=UserRole.EMPLOYEE)
    employee.password_hash = hash_password("pass123456")
    db_session.commit()
    login_as(client_factory, employee.email, "pass123456")
    r = client_factory.post(
        f"{GROUPS}/{group['id']}/import",
        files={"file": ("t.csv", b"email\na@example.test\n", "text/csv")},
        headers={"X-CSRF-Token": session_csrf_token(client_factory)},
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"
