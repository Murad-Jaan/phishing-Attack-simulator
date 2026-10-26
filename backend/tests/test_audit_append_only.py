import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import AuditLog, Organization


def _insert_audit_row(db_session: Session, organization: Organization) -> AuditLog:
    row = AuditLog(
        org_id=organization.id,
        action="test.action",
        entity_type="test",
        entity_id="1",
        after={"ok": True},
    )
    db_session.add(row)
    db_session.commit()
    return row


def test_audit_log_insert_is_allowed(
    db_session: Session, organization: Organization
) -> None:
    row = _insert_audit_row(db_session, organization)
    assert row.id is not None

    count = db_session.execute(text("SELECT count(*) FROM audit_log")).scalar_one()
    assert count == 1


def test_audit_log_update_is_blocked(
    db_session: Session, organization: Organization
) -> None:
    row = _insert_audit_row(db_session, organization)

    with pytest.raises(Exception, match="audit_log is append-only"):
        db_session.execute(
            text("UPDATE audit_log SET action = 'changed' WHERE id = :id"),
            {"id": row.id},
        )
        db_session.commit()


def test_audit_log_delete_is_blocked(
    db_session: Session, organization: Organization
) -> None:
    row = _insert_audit_row(db_session, organization)

    with pytest.raises(Exception, match="audit_log is append-only"):
        db_session.execute(text("DELETE FROM audit_log WHERE id = :id"), {"id": row.id})
        db_session.commit()


def test_audit_log_truncate_is_blocked(
    db_session: Session, organization: Organization
) -> None:
    _insert_audit_row(db_session, organization)

    with pytest.raises(Exception, match="audit_log is append-only"):
        db_session.execute(text("TRUNCATE audit_log"))
        db_session.commit()
