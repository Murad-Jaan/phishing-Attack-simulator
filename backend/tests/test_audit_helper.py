from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core import audit
from app.models import AuditLog, Organization


def test_audit_helper_redacts_secrets(db_session: Session, organization: Organization) -> None:
    metadata = {
        "password": "secret123",
        "token": "tok123",
        "csrf": "csrf123",
        "authorization": "Bearer xyz",
        "cookie": "session=abc",
        "hash": "hashvalue",
        "email": "test@example.test",
    }
    audit.write_audit(
        db_session,
        org_id=organization.id,
        actor_user_id=None,
        action="test.action",
        entity_type="test",
        entity_id="1",
        before=metadata,
        after={"ok": True},
    )
    db_session.commit()
    row = db_session.execute(text("SELECT before, after FROM audit_log ORDER BY id DESC LIMIT 1")).fetchone()
    before = row[0]
    after = row[1]
    before_str = str(before).lower()
    after_str = str(after).lower()
    assert "secret123" not in before_str
    assert "tok123" not in before_str
    assert "csrf123" not in before_str
    assert "bearer xyz" not in before_str
    assert "session=abc" not in before_str
    assert "hashvalue" not in before_str
    assert "password" not in before_str
    assert "token" not in before_str or '"token"' not in before_str
    assert "csrf" not in before_str
    assert "authorization" not in before_str
    assert "cookie" not in before_str
    assert '"hash"' not in before_str


def test_audit_helper_transaction_rollback(db_session: Session, organization: Organization) -> None:
    count_before = db_session.execute(text("SELECT count(*) FROM audit_log")).scalar_one()
    audit.write_audit(
        db_session,
        org_id=organization.id,
        actor_user_id=None,
        action="test.rollback",
        entity_type="test",
    )
    db_session.rollback()
    count_after = db_session.execute(text("SELECT count(*) FROM audit_log")).scalar_one()
    assert count_after == count_before


def test_audit_helper_no_truncate_or_update(db_session: Session, organization: Organization) -> None:
    audit.write_audit(
        db_session,
        org_id=organization.id,
        actor_user_id=None,
        action="test.append",
        entity_type="test",
    )
    db_session.commit()
    row_id = db_session.execute(text("SELECT id FROM audit_log ORDER BY id DESC LIMIT 1")).scalar_one()

    with __import__("pytest").raises(Exception):
        db_session.execute(text(f"UPDATE audit_log SET action='x' WHERE id={row_id}"))
        db_session.commit()
    db_session.rollback()

    with __import__("pytest").raises(Exception):
        db_session.execute(text(f"DELETE FROM audit_log WHERE id={row_id}"))
        db_session.commit()
    db_session.rollback()

    with __import__("pytest").raises(Exception):
        db_session.execute(text("TRUNCATE audit_log"))
        db_session.commit()
    db_session.rollback()
