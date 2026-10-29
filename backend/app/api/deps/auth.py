from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.core.cookies import SESSION_COOKIE_NAME
from app.services import session_service


def get_current_session(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE_NAME) or request.cookies.get("phishsim_session")
    if not token:
        raise HTTPException(status_code=401, detail="unauthenticated")
    sess = session_service.get_session_by_token(db, token)
    if not sess:
        raise HTTPException(status_code=401, detail="unauthenticated")
    return sess


def get_current_user(request: Request, db: Session = Depends(get_db), sess=Depends(get_current_session)):
    from app.models.user import User

    user = db.get(User, sess.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="unauthenticated")
    return user


def require_admin(user=Depends(get_current_user)):
    from app.models.user import UserRole

    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="forbidden")
    return user
