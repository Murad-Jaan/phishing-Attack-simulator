from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_session, require_staff
from app.core import csrf
from app.core.audit import write_audit
from app.core.errors import error_payload
from app.db import get_db
from app.models.group import Group, GroupMember
from app.models.organization import Organization
from app.models.target import Target
from app.services import groups_service

router = APIRouter()

CSV_TEMPLATE = "email,display_name\n"


def _error(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    fields: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_payload(request, code, message, fields or {}),
    )


def _get_group(db: Session, org_id, group_id: str) -> Group | None:
    group = db.get(Group, group_id)
    if group is None or group.org_id != org_id:
        return None
    return group


def _get_target(db: Session, org_id, target_id: str) -> Target | None:
    target = db.get(Target, target_id)
    if target is None or target.org_id != org_id:
        return None
    return target


def _min_group_size(db: Session, org_id) -> int:
    org = db.get(Organization, org_id)
    return org.min_group_size if org is not None else 5


def _audit(request: Request, db: Session, **kwargs: Any) -> None:
    write_audit(
        db,
        request_id=getattr(request.state, "request_id", None),
        ip=getattr(request.state, "client_ip", None),
        user_agent=request.headers.get("user-agent"),
        **kwargs,
    )


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


class GroupCreate(BaseModel):
    model_config = {"extra": "forbid"}

    name: str
    description: str | None = None
    department: str | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        name = value.strip()
        if not name or len(name) > 200:
            raise ValueError("Group name is required (200 characters or fewer).")
        return name


class GroupPatch(BaseModel):
    model_config = {"extra": "forbid"}

    name: str | None = None
    description: str | None = None
    department: str | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        name = value.strip()
        if not name or len(name) > 200:
            raise ValueError("Group name is required (200 characters or fewer).")
        return name


class TargetCreate(BaseModel):
    model_config = {"extra": "forbid"}

    email: str
    display_name: str | None = None

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        try:
            return groups_service.normalize_email(value)
        except ValueError as exc:
            raise ValueError("Enter a valid email address.") from exc


class TargetPatch(BaseModel):
    model_config = {"extra": "forbid"}

    email: str | None = None
    display_name: str | None = None

    @field_validator("email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            return groups_service.normalize_email(value)
        except ValueError as exc:
            raise ValueError("Enter a valid email address.") from exc


class MemberAdd(BaseModel):
    model_config = {"extra": "forbid"}

    target_id: str | None = None
    email: str | None = None
    display_name: str | None = None

    @field_validator("email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            return groups_service.normalize_email(value)
        except ValueError as exc:
            raise ValueError("Enter a valid email address.") from exc


@router.get("/api/v1/groups/import-template")
async def import_template(_user=Depends(require_staff)):
    return Response(
        content=CSV_TEMPLATE,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="targets-template.csv"',
        },
    )


@router.get("/api/v1/groups")
async def list_groups(
    db: Session = Depends(get_db), user=Depends(require_staff)
):
    org = db.get(Organization, user.org_id)
    min_size = org.min_group_size if org is not None else 5
    groups = db.execute(
        select(Group).where(Group.org_id == user.org_id).order_by(Group.name)
    ).scalars()
    return {
        "groups": [
            groups_service.serialize_group(db, g, min_size) for g in groups
        ]
    }


@router.post("/api/v1/groups", status_code=201)
async def create_group(
    req: GroupCreate,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    group = Group(
        org_id=user.org_id,
        name=req.name,
        description=_clean_optional(req.description),
        department=_clean_optional(req.department),
    )
    db.add(group)
    db.flush()
    _audit(
        request,
        db,
        org_id=group.org_id,
        actor_user_id=user.id,
        action="group.create",
        entity_type="group",
        entity_id=str(group.id),
        after={
            "name": group.name,
            "description": group.description,
            "department": group.department,
        },
    )
    db.commit()
    return {
        "group": groups_service.serialize_group(
            db, group, _min_group_size(db, user.org_id)
        )
    }


@router.get("/api/v1/groups/{group_id}")
async def get_group(
    group_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
):
    group = _get_group(db, user.org_id, group_id)
    if group is None:
        return _error(request, 404, "not_found", "Group not found")
    return {
        "group": groups_service.serialize_group(
            db,
            group,
            _min_group_size(db, user.org_id),
            include_members=True,
        )
    }


@router.patch("/api/v1/groups/{group_id}")
async def patch_group(
    group_id: str,
    req: GroupPatch,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    group = _get_group(db, user.org_id, group_id)
    if group is None:
        return _error(request, 404, "not_found", "Group not found")

    data = req.model_dump(exclude_unset=True)
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    for field in ("name", "description", "department"):
        if field not in data:
            continue
        value = data[field]
        if value is not None and field in ("description", "department"):
            value = _clean_optional(value)
        current = getattr(group, field)
        if current != value:
            before[field] = current
            after[field] = value
            setattr(group, field, value)

    if before:
        db.add(group)
        db.flush()
        _audit(
            request,
            db,
            org_id=group.org_id,
            actor_user_id=user.id,
            action="group.update",
            entity_type="group",
            entity_id=str(group.id),
            before=before,
            after=after,
        )
        db.commit()

    return {
        "group": groups_service.serialize_group(
            db, group, _min_group_size(db, user.org_id), include_members=True
        )
    }


@router.delete("/api/v1/groups/{group_id}")
async def delete_group(
    group_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    group = _get_group(db, user.org_id, group_id)
    if group is None:
        return _error(request, 404, "not_found", "Group not found")

    before = {
        "name": group.name,
        "description": group.description,
        "department": group.department,
        "member_count": groups_service.member_count(db, group.id),
    }
    _audit(
        request,
        db,
        org_id=group.org_id,
        actor_user_id=user.id,
        action="group.delete",
        entity_type="group",
        entity_id=str(group.id),
        before=before,
    )
    db.delete(group)
    db.commit()
    return {"ok": True}


@router.post("/api/v1/groups/{group_id}/members")
async def add_member(
    group_id: str,
    req: MemberAdd,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    group = _get_group(db, user.org_id, group_id)
    if group is None:
        return _error(request, 404, "not_found", "Group not found")

    if req.target_id is not None:
        target = _get_target(db, user.org_id, req.target_id)
        if target is None:
            return _error(request, 404, "not_found", "Target not found")
    elif req.email is not None:
        target = db.execute(
            select(Target).where(
                Target.org_id == user.org_id, Target.email == req.email
            )
        ).scalar_one_or_none()
        if target is None:
            target = Target(
                org_id=user.org_id,
                email=req.email,
                display_name=_clean_optional(req.display_name),
            )
            db.add(target)
            db.flush()
    else:
        return _error(
            request,
            422,
            "validation_error",
            "Provide a target_id or an email address",
            {"email": "Enter an email address or choose an existing target."},
        )

    exists = db.execute(
        select(GroupMember.id).where(
            GroupMember.group_id == group.id,
            GroupMember.target_id == target.id,
        )
    ).scalar_one_or_none()
    if exists is not None:
        return _error(
            request, 409, "duplicate_member", "This target is already in the group"
        )

    db.add(GroupMember(group_id=group.id, target_id=target.id))
    db.flush()
    _audit(
        request,
        db,
        org_id=group.org_id,
        actor_user_id=user.id,
        action="group.member_add",
        entity_type="group",
        entity_id=str(group.id),
        after={"target_id": str(target.id)},
    )
    db.commit()
    return {
        "member": groups_service.serialize_target(target),
        "group": groups_service.serialize_group(
            db, group, _min_group_size(db, user.org_id), include_members=True
        ),
    }


@router.delete("/api/v1/groups/{group_id}/members/{target_id}")
async def remove_member(
    group_id: str,
    target_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    group = _get_group(db, user.org_id, group_id)
    if group is None:
        return _error(request, 404, "not_found", "Group not found")

    membership = db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group.id,
            GroupMember.target_id == target_id,
        )
    ).scalar_one_or_none()
    if membership is None:
        return _error(request, 404, "not_found", "Membership not found")

    _audit(
        request,
        db,
        org_id=group.org_id,
        actor_user_id=user.id,
        action="group.member_remove",
        entity_type="group",
        entity_id=str(group.id),
        before={"target_id": target_id},
    )
    db.delete(membership)
    db.commit()
    return {
        "ok": True,
        "group": groups_service.serialize_group(
            db, group, _min_group_size(db, user.org_id), include_members=True
        ),
    }


@router.post("/api/v1/groups/{group_id}/import")
async def import_csv(
    group_id: str,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_staff),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    group = _get_group(db, user.org_id, group_id)
    if group is None:
        return _error(request, 404, "not_found", "Group not found")

    data = await file.read(groups_service.CSV_MAX_BYTES + 1)
    if len(data) > groups_service.CSV_MAX_BYTES:
        return _error(
            request,
            413,
            "file_too_large",
            "CSV files must be 5 MB or smaller",
            {"file": "The uploaded file exceeds the 5 MB limit."},
        )

    org = db.get(Organization, user.org_id)
    if org is None:
        return _error(request, 404, "not_found", "Organization not found")

    try:
        result = groups_service.import_targets(db, org, group, data)
    except groups_service.CsvFileError as exc:
        return _error(
            request, 422, "validation_error", str(exc), {"file": str(exc)}
        )

    _audit(
        request,
        db,
        org_id=group.org_id,
        actor_user_id=user.id,
        action="group.import",
        entity_type="group",
        entity_id=str(group.id),
        after={
            "imported": result["imported"],
            "skipped": result["skipped"],
            "total": result["total"],
            "errors": result["skipped"],
        },
    )
    db.commit()
    return {
        "result": result,
        "group": groups_service.serialize_group(
            db, group, org.min_group_size, include_members=True
        ),
    }


# ---------------------------------------------------------------------------
# Targets CRUD
# ---------------------------------------------------------------------------


@router.get("/api/v1/targets")
async def list_targets(
    db: Session = Depends(get_db), user=Depends(require_staff)
):
    targets = db.execute(
        select(Target).where(Target.org_id == user.org_id).order_by(Target.email)
    ).scalars()
    return {"targets": [groups_service.serialize_target(t) for t in targets]}


@router.post("/api/v1/targets", status_code=201)
async def create_target(
    req: TargetCreate,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    existing = db.execute(
        select(Target).where(
            Target.org_id == user.org_id, Target.email == req.email
        )
    ).scalar_one_or_none()
    if existing is not None:
        return _error(
            request, 409, "duplicate_target", "A target with this email already exists"
        )

    target = Target(
        org_id=user.org_id,
        email=req.email,
        display_name=_clean_optional(req.display_name),
    )
    db.add(target)
    db.flush()
    _audit(
        request,
        db,
        org_id=target.org_id,
        actor_user_id=user.id,
        action="target.create",
        entity_type="target",
        entity_id=str(target.id),
        after={"email": target.email, "display_name": target.display_name},
    )
    db.commit()
    return {"target": groups_service.serialize_target(target)}


@router.get("/api/v1/targets/{target_id}")
async def get_target(
    target_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
):
    target = _get_target(db, user.org_id, target_id)
    if target is None:
        return _error(request, 404, "not_found", "Target not found")
    return {"target": groups_service.serialize_target(target)}


@router.patch("/api/v1/targets/{target_id}")
async def patch_target(
    target_id: str,
    req: TargetPatch,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    target = _get_target(db, user.org_id, target_id)
    if target is None:
        return _error(request, 404, "not_found", "Target not found")

    data = req.model_dump(exclude_unset=True)
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    for field in ("email", "display_name"):
        if field not in data:
            continue
        value = data[field]
        if field == "display_name":
            value = _clean_optional(value)
        current = getattr(target, field)
        if current != value:
            before[field] = current
            after[field] = value
            setattr(target, field, value)

    if before:
        if "email" in after:
            duplicate = db.execute(
                select(Target).where(
                    Target.org_id == user.org_id,
                    Target.email == after["email"],
                    Target.id != target.id,
                )
            ).scalar_one_or_none()
            if duplicate is not None:
                return _error(
                    request,
                    409,
                    "duplicate_target",
                    "A target with this email already exists",
                )
        db.add(target)
        db.flush()
        _audit(
            request,
            db,
            org_id=target.org_id,
            actor_user_id=user.id,
            action="target.update",
            entity_type="target",
            entity_id=str(target.id),
            before=before,
            after=after,
        )
        db.commit()

    return {"target": groups_service.serialize_target(target)}


@router.delete("/api/v1/targets/{target_id}")
async def delete_target(
    target_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    target = _get_target(db, user.org_id, target_id)
    if target is None:
        return _error(request, 404, "not_found", "Target not found")

    _audit(
        request,
        db,
        org_id=target.org_id,
        actor_user_id=user.id,
        action="target.delete",
        entity_type="target",
        entity_id=str(target.id),
        before={"email": target.email, "display_name": target.display_name},
    )
    db.delete(target)
    db.commit()
    return {"ok": True}
