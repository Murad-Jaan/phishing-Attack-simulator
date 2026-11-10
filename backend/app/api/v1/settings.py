from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_session, require_admin
from app.core import csrf
from app.core.errors import error_payload
from app.db import get_db
from app.models.organization import Organization
from app.services import retention_service, settings_service


router = APIRouter()


class PatchOrgSettingsRequest(BaseModel):
    model_config = {"extra": "forbid"}

    name: str | None = None
    primary_domain: str | None = None
    timezone: str | None = None
    retention_days: int | None = None
    min_group_size: int | None = None
    send_domain_allowlist: list[str] | None = None


def _validation_response(request: Request, fields: dict[str, str]) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_payload(request, "validation_error", "Invalid settings", fields),
    )


@router.get("/settings/retention/preview")
@router.get("/api/v1/settings/retention/preview")
async def preview_retention(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Read-only retention counts for the admin's organization.

    The response contains scope names and integer counts only; it never
    includes session tokens, hashes, or other sensitive row data.
    """
    return {"scopes": retention_service.preview(db, org_id=admin.org_id)}


@router.get("/settings/organization")
@router.get("/api/v1/settings/organization")
async def get_org_settings(
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    org = db.get(Organization, admin.org_id)
    if org is None:
        return JSONResponse(
            status_code=404,
            content=error_payload(request, "not_found", "Organization not found", {}),
        )
    return {"settings": settings_service.settings_payload(org)}


@router.patch("/settings/organization")
@router.patch("/api/v1/settings/organization")
async def patch_org_settings(
    req: PatchOrgSettingsRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
    sess=Depends(get_current_session),
):
    # Check order: 401 (auth) -> 403 (RBAC) -> 403 (CSRF) -> 422 (validation).
    csrf.assert_session_csrf(request, str(sess.id))

    org = db.get(Organization, admin.org_id)
    if org is None:
        return JSONResponse(
            status_code=404,
            content=error_payload(request, "not_found", "Organization not found", {}),
        )

    data: dict[str, Any] = req.model_dump(exclude_unset=True)
    try:
        normalized = settings_service.validate_settings(data)
    except settings_service.SettingsValidationError as exc:
        return _validation_response(request, exc.fields)

    changed = settings_service.update_organization_settings(
        db,
        org,
        normalized,
        actor_user_id=admin.id,
        request_id=getattr(request.state, "request_id", None),
        ip=getattr(request.state, "client_ip", None),
        user_agent=request.headers.get("user-agent"),
    )
    if changed:
        db.commit()
    return {"settings": settings_service.settings_payload(org)}
