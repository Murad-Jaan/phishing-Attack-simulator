from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps.auth import require_admin, get_current_user
from app.core.audit import write_audit
from app.core.errors import error_payload
from app.db import get_db
from app.models.user import User, UserRole
from app.services import session_service


router = APIRouter()


@router.get("/users")
async def list_users(request: Request, db: Session = Depends(get_db), admin=Depends(require_admin)):
    users = db.query(User).all()
    return [
        {"id": str(u.id), "email": u.email, "role": u.role.value, "is_active": u.is_active, "org_id": str(u.org_id)}
        for u in users
    ]


class PatchUserRequest(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


@router.patch("/users/{user_id}")
async def patch_user(user_id: str, req: PatchUserRequest, request: Request, db: Session = Depends(get_db), admin=Depends(require_admin), current=Depends(get_current_user)):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="not_found")
    if target.org_id != admin.org_id:
        raise HTTPException(status_code=404, detail="not_found")
    before = {"role": target.role.value, "is_active": target.is_active}
    changed = False
    if req.role is not None and req.role != target.role:
        if target.role == UserRole.ADMIN and req.role != UserRole.ADMIN:
            from sqlalchemy import func, select

            cnt = db.execute(select(func.count(User.id)).where(User.org_id == target.org_id, User.role == UserRole.ADMIN, User.is_active == True)).scalar_one()
            if cnt <= 1:
                from fastapi.responses import JSONResponse

                return JSONResponse(status_code=409, content=error_payload(request, "last_admin_guard", "Cannot demote the last admin", {}))
        target.role = req.role
        changed = True
    if req.is_active is not None and req.is_active != target.is_active:
        if target.is_active is True and req.is_active is False and target.role == UserRole.ADMIN:
            from sqlalchemy import func, select

            cnt = db.execute(select(func.count(User.id)).where(User.org_id == target.org_id, User.role == UserRole.ADMIN, User.is_active == True)).scalar_one()
            if cnt <= 1:
                from fastapi.responses import JSONResponse

                return JSONResponse(status_code=409, content=error_payload(request, "last_admin_guard", "Cannot deactivate the last admin", {}))
        target.is_active = req.is_active
        changed = True
    if not changed:
        return {"user": {"id": str(target.id), "email": target.email, "role": target.role.value, "is_active": target.is_active}}
    db.add(target)
    db.flush()
    if req.role is not None and req.role != before["role"]:
        session_service.revoke_all_user_sessions(db, target.id)
    if req.is_active is not None and req.is_active is False and req.is_active != before["is_active"]:
        session_service.revoke_all_user_sessions(db, target.id)
    write_audit(
        db,
        org_id=target.org_id,
        actor_user_id=admin.id,
        action="user.update",
        entity_type="user",
        entity_id=str(target.id),
        before=before,
        after={"role": target.role.value, "is_active": target.is_active},
        request_id=getattr(request.state, "request_id", None),
        ip=getattr(request.state, "client_ip", None),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return {"user": {"id": str(target.id), "email": target.email, "role": target.role.value, "is_active": target.is_active}}
