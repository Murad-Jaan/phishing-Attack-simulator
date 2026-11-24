from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.session import AuthSession
from app.models.user import User


SESSION_IDLE_MINUTES = 60
SESSION_ABSOLUTE_HOURS = 8


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user: User) -> tuple[AuthSession, str]:
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    now = datetime.now(timezone.utc)
    import os
    csrf_secret = os.getenv("CSRF_SECRET", "")
    import hmac
    import hashlib
    csrf_hash = hmac.new(csrf_secret.encode(), token.encode(), hashlib.sha256).digest() if csrf_secret else hashlib.sha256(token.encode()).digest()
    sess = AuthSession(
        user_id=user.id,
        token_hash=token_hash.encode() if False else __import__("hashlib").sha256(token.encode()).digest()[:32] if False else None,  # will fix below
    )
    # build properly
    sess = AuthSession(
        user_id=user.id,
        token_hash=__import__("hashlib").sha256(token.encode()).digest(),
        csrf_hash=csrf_hash,
        expires_at=now + timedelta(hours=SESSION_ABSOLUTE_HOURS),
        last_seen_at=now,
        revoked_at=None,
    )
    db.add(sess)
    db.flush()
    return sess, token


def rotate_session(db: Session, old: AuthSession, user: User) -> tuple[AuthSession, str]:
    old.revoked_at = datetime.now(timezone.utc)
    db.add(old)
    return create_session(db, user)


def _touch_last_seen(
    db: Session, session_id, previous: datetime, now: datetime
) -> None:
    bind = db.get_bind()
    engine = getattr(bind, "engine", bind)
    touch = Session(bind=engine)
    try:
        touch.execute(
            update(AuthSession)
            .where(
                AuthSession.id == session_id,
                AuthSession.last_seen_at == previous,
            )
            .values(last_seen_at=now)
        )
        touch.commit()
    except Exception:
        touch.rollback()
    finally:
        touch.close()


def get_session_by_token(db: Session, token: str) -> AuthSession | None:
    token_hash = __import__("hashlib").sha256(token.encode()).digest()
    stmt = select(AuthSession).where(AuthSession.token_hash == token_hash)
    res = db.execute(stmt)
    sess = res.scalar_one_or_none()
    if not sess:
        return None
    if sess.revoked_at is not None:
        return None
    now = datetime.now(timezone.utc)
    if sess.expires_at < now:
        return None
    last = getattr(sess, "last_seen_at", None)
    if last and (now - last) > timedelta(minutes=SESSION_IDLE_MINUTES):
        return None
    user = db.get(User, sess.user_id)
    if not user or not user.is_active:
        return None
    if last is not None and (now - last) > timedelta(minutes=1):
        _touch_last_seen(db, sess.id, last, now)
    return sess


def revoke_session(db: Session, sess: AuthSession) -> None:
    sess.revoked_at = datetime.now(timezone.utc)
    db.add(sess)
    db.flush()


def revoke_all_user_sessions(db: Session, user_id) -> None:
    now = datetime.now(timezone.utc)
    stmt = update(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None)).values(revoked_at=now)
    db.execute(stmt)
    db.flush()
