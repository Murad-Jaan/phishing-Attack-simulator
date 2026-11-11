from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_session, require_template_author
from app.core import csrf
from app.core.errors import error_payload
from app.db import get_db
from app.models.template import Template
from app.services import template_service


router = APIRouter()


class RedFlagInput(BaseModel):
    model_config = {"extra": "forbid"}

    label: str
    explanation: str


class CreateTemplateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    name: str
    sender: str
    subject: str
    body: str
    difficulty: str
    attack_technique_id: str
    lure_type: str
    status: str = "draft"
    red_flags: list[RedFlagInput] = Field(default_factory=list)


class UpdateTemplateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    name: str | None = None
    sender: str | None = None
    subject: str | None = None
    body: str | None = None
    difficulty: str | None = None
    attack_technique_id: str | None = None
    lure_type: str | None = None
    status: str | None = None
    red_flags: list[RedFlagInput] | None = None


class DuplicateTemplateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    name: str | None = None


def _validation_response(request: Request, fields: dict[str, str]) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_payload(
            request, "validation_error", "Invalid template content", fields
        ),
    )


def _conflict_response(request: Request, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=error_payload(request, code, message, {}),
    )


def _get_template(db: Session, org_id: uuid.UUID, template_id: str) -> Template | None:
    try:
        tid = uuid.UUID(template_id)
    except (ValueError, TypeError):
        return None
    template = db.get(Template, tid)
    if template is None or template.org_id != org_id:
        return None
    return template


def _not_found(request: Request) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=error_payload(request, "not_found", "Template not found", {}),
    )


@router.get("/templates")
@router.get("/api/v1/templates")
async def list_templates(
    request: Request,
    search: str | None = None,
    difficulty: str | None = None,
    technique: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_template_author),
):
    stmt = template_service.latest_templates_query(user.org_id)
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Template.name.ilike(term),
                Template.subject.ilike(term),
                Template.sender.ilike(term),
            )
        )
    if difficulty:
        stmt = stmt.where(Template.difficulty == difficulty)
    if technique:
        value = "none" if technique.strip().lower() in ("none", "n/a", "") else technique.strip().upper()
        stmt = stmt.where(Template.attack_technique_id == value)
    if status:
        stmt = stmt.where(Template.status == status)
    stmt = stmt.order_by(Template.updated_at.desc(), Template.name.asc())

    rows = list(db.execute(stmt).scalars().unique())
    return {
        "templates": [template_service.template_payload(t) for t in rows],
        "total": len(rows),
    }


@router.get("/templates/{template_id}")
@router.get("/api/v1/templates/{template_id}")
async def get_template(
    template_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_template_author),
):
    template = _get_template(db, user.org_id, template_id)
    if template is None:
        return _not_found(request)
    return {"template": template_service.template_payload(template)}


@router.get("/templates/{template_id}/preview")
@router.get("/api/v1/templates/{template_id}/preview")
async def preview_template(
    template_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_template_author),
):
    template = _get_template(db, user.org_id, template_id)
    if template is None:
        return _not_found(request)
    return {"preview": template_service.render_preview(template)}


@router.post("/templates", status_code=201)
@router.post("/api/v1/templates", status_code=201)
async def create_template(
    req: CreateTemplateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_template_author),
    sess=Depends(get_current_session),
):
    # Check order: 401 -> 403 RBAC -> 403 CSRF -> 422 validation.
    csrf.assert_session_csrf(request, str(sess.id))
    try:
        template = template_service.create_template(
            db,
            org_id=user.org_id,
            actor_id=user.id,
            data=req.model_dump(),
            request=request,
        )
    except template_service.TemplateValidationError as exc:
        return _validation_response(request, exc.fields)
    db.commit()
    return {"template": template_service.template_payload(template)}


@router.patch("/templates/{template_id}")
@router.patch("/api/v1/templates/{template_id}")
async def update_template(
    template_id: str,
    req: UpdateTemplateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_template_author),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    template = _get_template(db, user.org_id, template_id)
    if template is None:
        return _not_found(request)
    data: dict[str, Any] = req.model_dump(exclude_unset=True)
    try:
        template = template_service.update_template(
            db,
            template,
            actor_id=user.id,
            data=data,
            request=request,
        )
    except template_service.TemplateValidationError as exc:
        return _validation_response(request, exc.fields)
    except template_service.TemplateConflictError as exc:
        return _conflict_response(request, exc.code, exc.message)
    db.commit()
    return {"template": template_service.template_payload(template)}


@router.post("/templates/{template_id}/duplicate", status_code=201)
@router.post("/api/v1/templates/{template_id}/duplicate", status_code=201)
async def duplicate_template(
    template_id: str,
    request: Request,
    req: DuplicateTemplateRequest | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_template_author),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    template = _get_template(db, user.org_id, template_id)
    if template is None:
        return _not_found(request)
    try:
        copy = template_service.duplicate_template(
            db,
            template,
            actor_id=user.id,
            name=req.name if req else None,
            request=request,
        )
    except template_service.TemplateValidationError as exc:
        return _validation_response(request, exc.fields)
    db.commit()
    return {"template": template_service.template_payload(copy)}


@router.post("/templates/{template_id}/archive")
@router.post("/api/v1/templates/{template_id}/archive")
async def archive_template(
    template_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_template_author),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    template = _get_template(db, user.org_id, template_id)
    if template is None:
        return _not_found(request)
    template = template_service.archive_template(
        db,
        template,
        actor_id=user.id,
        request=request,
    )
    db.commit()
    return {"template": template_service.template_payload(template)}
