from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import csrf, cookies
from app.core.audit import write_audit
from app.core import rate_limit
from app.db import get_db
from app.models.user import User
from app.services import session_service
from app.api.deps.auth import get_current_session, get_current_user


router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.get("/api/v1/auth/csrf")
async def get_csrf(request: Request, response: Response, db: Session = Depends(get_db)):
    token = csrf.issue_login_csrf(response)
    return {"csrf_token": token}


@router.post("/auth/login")
async def login(req: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    csrf_cookie = csrf.get_csrf_cookie(request)
    csrf_header = request.headers.get("X-CSRF-Token")
    if csrf_cookie and csrf_header and csrf.verify_csrf_token(csrf_cookie, None):
        pass
    elif not csrf.check_origin(request):
        if not (csrf_cookie and csrf_header and csrf.verify_csrf_token(csrf_cookie, None)):
            raise HTTPException(status_code=403, detail="csrf_failed")
    rl = rate_limit.check_rate_limit_request(request, req.email)
    if not rl.allowed:
        raise HTTPException(status_code=429, headers={"Retry-After": str(rl.retry_after or 60)}, detail="rate_limited")
    stmt = select(User).where(User.email == req.email.lower())
    res = db.execute(stmt)
    user = res.scalar_one_or_none()
    from app.core.security import needs_rehash, hash_password

    from app.core import security

    ok: bool
    if user is None:
        try:
            security.verify_password_with_dummy(None, req.password)
        except Exception:
            pass
        rate_limit.record_fail_for(req.email)
        raise HTTPException(status_code=401, detail="invalid_credentials")
    try:
        ok = bool(security.ph.verify(user.password_hash, req.password))
    except Exception:
        ok = False
    if not ok or not user.is_active:
        rate_limit.record_fail_for(req.email)
        raise HTTPException(status_code=401, detail="invalid_credentials")
    rate_limit.record_success_for(req.email)
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(req.password)
        db.add(user)
    sess, token = session_service.create_session(db, user)
    cookies.set_session_cookie(response, token)
    csrf.issue_session_csrf(response, str(sess.id))
    write_audit(
        db,
        org_id=user.org_id,
        actor_user_id=user.id,
        action="auth.login",
        entity_type="user",
        entity_id=str(user.id),
        before=None,
        after={"email": user.email},
        request_id=getattr(request.state, "request_id", None),
        ip=getattr(request.state, "client_ip", None),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return {"user": {"id": str(user.id), "email": user.email, "role": user.role.value}}


@router.post("/auth/logout")
async def logout(request: Request, response: Response, db: Session = Depends(get_db), sess=Depends(get_current_session)):
    csrf_cookie = csrf.get_csrf_cookie(request)
    csrf_header = request.headers.get("X-CSRF-Token")
    if not csrf_cookie or not csrf_header or not csrf.verify_csrf_token(csrf_cookie, str(sess.id)):
        raise HTTPException(status_code=403, detail="csrf_failed")
    session_service.revoke_session(db, sess)
    user = db.get(User, sess.user_id)
    write_audit(
        db,
        org_id=user.org_id if user else None,
        actor_user_id=user.id if user else None,
        action="auth.logout",
        entity_type="session",
        entity_id=str(sess.id),
        before=None,
        after=None,
        request_id=getattr(request.state, "request_id", None),
        ip=getattr(request.state, "client_ip", None),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    response.delete_cookie(cookies.SESSION_COOKIE_NAME, path="/")
    response.delete_cookie("phishsim_session", path="/")
    response.delete_cookie(cookies.CSRF_COOKIE_NAME, path="/")
    response.delete_cookie("phishsim_csrf", path="/")
    return {"ok": True}


@router.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return {"user": {"id": str(user.id), "email": user.email, "role": user.role.value, "org_id": str(user.org_id)}}
