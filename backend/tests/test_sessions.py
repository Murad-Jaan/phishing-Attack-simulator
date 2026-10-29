from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.services import session_service


def test_token_stored_only_as_hash(db_session: Session, organization: Organization):
    from app.models.session import AuthSession

    user = User(email="u1@example.com", password_hash=hash_password("pass"), org_id=organization.id, role=UserRole.EMPLOYEE, display_name="u1")
    db_session.add(user)
    db_session.commit()
    sess, token = session_service.create_session(db_session, user)
    db_session.commit()
    row = db_session.get(AuthSession, sess.id)
    assert row.token_hash != token.encode()
    assert len(row.token_hash) == 32


def test_rotation_on_login(db_session: Session, organization: Organization):
    user = User(email="u2@example.com", password_hash=hash_password("pass"), org_id=organization.id, role=UserRole.EMPLOYEE, display_name='u')
    db_session.add(user)
    db_session.commit()
    s1, t1 = session_service.create_session(db_session, user)
    db_session.commit()
    s2, t2 = session_service.rotate_session(db_session, s1, user)
    db_session.commit()
    db_session.refresh(s1)
    assert s1.revoked_at is not None


def test_logout_revokes(db_session: Session, organization: Organization):
    user = User(email="u3@example.com", password_hash=hash_password("pass"), org_id=organization.id, role=UserRole.EMPLOYEE, display_name='u')
    db_session.add(user)
    db_session.commit()
    s, t = session_service.create_session(db_session, user)
    db_session.commit()
    session_service.revoke_session(db_session, s)
    db_session.commit()
    db_session.refresh(s)
    assert s.revoked_at is not None


def test_expired_revoked_deactivated_idle_rejected(db_session: Session, organization: Organization):
    user = User(email="u4@example.com", password_hash=hash_password("pass"), org_id=organization.id, role=UserRole.EMPLOYEE, display_name='u')
    db_session.add(user)
    db_session.commit()
    s, t = session_service.create_session(db_session, user)
    db_session.commit()
    # expired
    s.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()
    assert session_service.get_session_by_token(db_session, t) is None
    # revoked
    user2 = User(email="u5@example.com", password_hash=hash_password("pass"), org_id=organization.id, role=UserRole.EMPLOYEE, display_name='u')
    db_session.add(user2)
    db_session.commit()
    s2, t2 = session_service.create_session(db_session, user2)
    db_session.commit()
    session_service.revoke_session(db_session, s2)
    db_session.commit()
    assert session_service.get_session_by_token(db_session, t2) is None
    # deactivated
    user3 = User(email="u6@example.com", password_hash=hash_password("pass"), org_id=organization.id, role=UserRole.EMPLOYEE, display_name='u')
    db_session.add(user3)
    db_session.commit()
    s3, t3 = session_service.create_session(db_session, user3)
    db_session.commit()
    user3.is_active = False
    db_session.commit()
    assert session_service.get_session_by_token(db_session, t3) is None
    # idle
    user4 = User(email="u7@example.com", password_hash=hash_password("pass"), org_id=organization.id, role=UserRole.EMPLOYEE, display_name='u')
    db_session.add(user4)
    db_session.commit()
    s4, t4 = session_service.create_session(db_session, user4)
    db_session.commit()
    s4.last_seen_at = datetime.now(timezone.utc) - timedelta(minutes=61)
    db_session.commit()
    assert session_service.get_session_by_token(db_session, t4) is None


def test_idle_slide_never_passes_absolute_limit(db_session: Session, organization: Organization):
    user = User(email="u8@example.com", password_hash=hash_password("pass"), org_id=organization.id, role=UserRole.EMPLOYEE, display_name='u')
    db_session.add(user)
    db_session.commit()
    s, t = session_service.create_session(db_session, user)
    db_session.commit()
    s.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    s.last_used_at = datetime.now(timezone.utc)
    db_session.commit()
    assert session_service.get_session_by_token(db_session, t) is None
