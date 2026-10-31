from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps.auth import require_admin, get_current_user
from app.core.audit import write_audit
from app.core.errors import error_payload
from app.db import get_db
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.services import session_service


router = APIRouter()


@router.get("/users")
@router.get("/api/v1/users")
async def list_users(request: Request, db: Session = Depends(get_db), admin=Depends(require_admin)):
    users = db.query(User).all()
    return [
        {"id": str(u.id), "email": u.email, "role": u.role.value, "is_active": u.is_active, "org_id": str(u.org_id)}
        for u in users
    ]


class PatchUserRequest(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


def error_response_409(request: Request, message: str):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=409,
        content=error_payload(request, "last_admin_guard", message, {}),
    )


@router.patch("/users/{user_id}")
@router.patch("/api/v1/users/{user_id}")
async def patch_user(user_id: str, req: PatchUserRequest, request: Request, db: Session = Depends(get_db), admin=Depends(require_admin), current=Depends(get_current_user)):
    from sqlalchemy import func, select

    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="not_found")
    if target.org_id != admin.org_id:
        raise HTTPException(status_code=404, detail="not_found")
    original_role = target.role
    original_is_active = target.is_active
    before = {"role": original_role.value, "is_active": original_is_active}
    demoting = (
        req.role is not None
        and req.role != original_role
        and original_role == UserRole.ADMIN
        and req.role != UserRole.ADMIN
    )
    deactivating = req.is_active is False and original_is_active is True and original_role == UserRole.ADMIN
    if demoting or deactivating:
        # row lock on the org serializes concurrent guard checks
        db.execute(
            select(Organization.id)
            .where(Organization.id == target.org_id)
            .with_for_update()
        )
        cnt = db.execute(
            select(func.count(User.id)).where(
                User.org_id == target.org_id,
                User.role == UserRole.ADMIN,
                User.is_active.is_(True),
            )
        ).scalar_one()
        if demoting and cnt <= 1:
            return error_response_409(request, "Cannot demote the last admin")
        if deactivating and cnt <= 1:
            return error_response_409(request, "Cannot deactivate the last admin")
    changed = False
    if req.role is not None and req.role != original_role:
        target.role = req.role
        changed = True
    if req.is_active is not None and req.is_active != original_is_active:
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
