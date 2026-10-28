from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

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
    sess = AuthSession(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=now + timedelta(hours=SESSION_ABSOLUTE_HOURS),
        last_used_at=now,
        revoked_at=None,
    )
    db.add(sess)
    db.flush()
    return sess, token


def rotate_session(db: Session, old: AuthSession, user: User) -> tuple[AuthSession, str]:
    old.revoked_at = datetime.now(timezone.utc)
    db.add(old)
    return create_session(db, user)


def get_session_by_token(db: Session, token: str) -> AuthSession | None:
    token_hash = _hash_token(token)
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
    if sess.last_used_at and (now - sess.last_used_at) > timedelta(minutes=SESSION_IDLE_MINUTES):
        return None
    # sliding
    sess.last_used_at = now
    db.add(sess)
    db.flush()
    # check user active
    user = db.get(User, sess.user_id)
    if not user or not user.is_active:
        return None
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
