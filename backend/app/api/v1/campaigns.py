from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_session, require_admin, require_staff
from app.core import csrf
from app.core.audit import write_audit
from app.core.errors import error_payload
from app.db import get_db
from app.models.campaign import (
    Authorization,
    AuthorizationStatus,
    Campaign,
    CampaignStatus,
)
from app.models.group import Group
from app.models.organization import Organization
from app.models.template import Template, TemplateStatus
from app.services import campaign_service

router = APIRouter()


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


def _audit(request: Request, db: Session, **kwargs: Any) -> None:
    write_audit(
        db,
        request_id=getattr(request.state, "request_id", None),
        ip=getattr(request.state, "client_ip", None),
        user_agent=request.headers.get("user-agent"),
        **kwargs,
    )


def _uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _get_campaign(db: Session, org_id: uuid.UUID, campaign_id: str) -> Campaign | None:
    cid = _uuid(campaign_id)
    if cid is None:
        return None
    campaign = db.get(Campaign, cid)
    if campaign is None or campaign.org_id != org_id:
        return None
    return campaign


def _get_authorization(
    db: Session, org_id: uuid.UUID, authorization_id: str
) -> Authorization | None:
    aid = _uuid(authorization_id)
    if aid is None:
        return None
    auth = db.get(Authorization, aid)
    if auth is None or auth.org_id != org_id:
        return None
    return auth


def _org(db: Session, org_id: uuid.UUID) -> Organization:
    org = db.get(Organization, org_id)
    assert org is not None
    return org


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


class CampaignCreate(BaseModel):
    model_config = {"extra": "forbid"}

    name: str
    description: str | None = None
    template_id: str | None = None
    group_id: str | None = None
    send_time: datetime | None = None
    sending_domain: str | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        name = value.strip()
        if not name or len(name) > 200:
            raise ValueError("Campaign name is required (200 characters or fewer).")
        return name


class CampaignPatch(BaseModel):
    model_config = {"extra": "forbid"}

    name: str | None = None
    description: str | None = None
    template_id: str | None = None
    group_id: str | None = None
    send_time: datetime | None = None
    sending_domain: str | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        name = value.strip()
        if not name or len(name) > 200:
            raise ValueError("Campaign name is required (200 characters or fewer).")
        return name


class AuthorizationRequest(BaseModel):
    model_config = {"extra": "forbid"}

    valid_from: datetime | None = None
    valid_until: datetime | None = None
    note: str | None = None


class ApprovalDecision(BaseModel):
    model_config = {"extra": "forbid"}

    note: str | None = None


class RejectionDecision(BaseModel):
    model_config = {"extra": "forbid"}

    reason: str

    @field_validator("reason")
    @classmethod
    def _reason(cls, value: str) -> str:
        reason = value.strip()
        if not reason:
            raise ValueError("A rejection reason is required.")
        if len(reason) > 2000:
            raise ValueError("The rejection reason must be 2000 characters or fewer.")
        return reason


class TestSendRequest(BaseModel):
    model_config = {"extra": "forbid"}

    recipient: str | None = None


def _apply_template(
    db: Session, org_id: uuid.UUID, campaign: Campaign, template_id: str | None
) -> None:
    if template_id is None:
        campaign.template_id = None
        campaign.template_version = None
        return
    tid = _uuid(template_id)
    template = db.get(Template, tid) if tid else None
    if template is None or template.org_id != org_id:
        raise campaign_service.CampaignValidationError(
            {"template_id": "Select a template in this organization."}
        )
    if template.status != TemplateStatus.PUBLISHED:
        raise campaign_service.CampaignValidationError(
            {"template_id": "Only published templates can be used in a campaign."}
        )
    campaign.template_id = template.id
    campaign.template_version = template.version


def _apply_group(
    db: Session, org_id: uuid.UUID, campaign: Campaign, group_id: str | None
) -> None:
    if group_id is None:
        campaign.group_id = None
        return
    gid = _uuid(group_id)
    group = db.get(Group, gid) if gid else None
    if group is None or group.org_id != org_id:
        raise campaign_service.CampaignValidationError(
            {"group_id": "Select a group in this organization."}
        )
    campaign.group_id = group.id


@router.get("/api/v1/campaigns")
@router.get("/campaigns")
async def list_campaigns(
    db: Session = Depends(get_db), user=Depends(require_staff)
):
    rows = list(
        db.execute(
            select(Campaign)
            .where(Campaign.org_id == user.org_id)
            .order_by(Campaign.updated_at.desc(), Campaign.name.asc())
        ).scalars()
    )
    return {
        "campaigns": [campaign_service.serialize_campaign(db, c) for c in rows],
        "total": len(rows),
    }


@router.post("/api/v1/campaigns", status_code=201)
@router.post("/campaigns", status_code=201)
async def create_campaign(
    req: CampaignCreate,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    org = _org(db, user.org_id)
    campaign = Campaign(
        org_id=user.org_id,
        name=req.name,
        description=_clean(req.description),
        send_time=req.send_time,
        sending_domain=(req.sending_domain or org.primary_domain).strip().lower(),
        status=CampaignStatus.DRAFT,
        created_by=user.id,
    )
    try:
        _apply_template(db, user.org_id, campaign, req.template_id)
        _apply_group(db, user.org_id, campaign, req.group_id)
    except campaign_service.CampaignValidationError as exc:
        return _error(request, 422, "validation_error", "Invalid campaign", exc.fields)
    db.add(campaign)
    db.flush()
    _audit(
        request,
        db,
        org_id=campaign.org_id,
        actor_user_id=user.id,
        action="campaign.create",
        entity_type="campaign",
        entity_id=str(campaign.id),
        after={
            "name": campaign.name,
            "template_id": str(campaign.template_id) if campaign.template_id else None,
            "group_id": str(campaign.group_id) if campaign.group_id else None,
            "send_time": campaign.send_time.isoformat() if campaign.send_time else None,
            "sending_domain": campaign.sending_domain,
            "status": campaign.status.value,
        },
    )
    db.commit()
    return {"campaign": campaign_service.serialize_campaign(db, campaign)}


@router.get("/api/v1/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
):
    campaign = _get_campaign(db, user.org_id, campaign_id)
    if campaign is None:
        return _error(request, 404, "not_found", "Campaign not found")
    return {"campaign": campaign_service.serialize_campaign(db, campaign)}


@router.patch("/api/v1/campaigns/{campaign_id}")
async def patch_campaign(
    campaign_id: str,
    req: CampaignPatch,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    campaign = _get_campaign(db, user.org_id, campaign_id)
    if campaign is None:
        return _error(request, 404, "not_found", "Campaign not found")
    if campaign.status not in (CampaignStatus.DRAFT, CampaignStatus.APPROVED):
        return _error(
            request,
            409,
            "campaign_locked",
            "This campaign can no longer be edited.",
        )

    data = req.model_dump(exclude_unset=True)
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    scope_changed = False

    before["name"] = campaign.name
    before["description"] = campaign.description
    before["template_id"] = str(campaign.template_id) if campaign.template_id else None
    before["group_id"] = str(campaign.group_id) if campaign.group_id else None
    before["send_time"] = campaign.send_time.isoformat() if campaign.send_time else None
    before["sending_domain"] = campaign.sending_domain

    try:
        if "name" in data and data["name"] is not None:
            campaign.name = data["name"]
        if "description" in data:
            campaign.description = _clean(data["description"])
        if "template_id" in data:
            _apply_template(db, user.org_id, campaign, data["template_id"])
        if "group_id" in data:
            _apply_group(db, user.org_id, campaign, data["group_id"])
        if "send_time" in data:
            campaign.send_time = data["send_time"]
        if "sending_domain" in data and data["sending_domain"] is not None:
            campaign.sending_domain = data["sending_domain"].strip().lower()
    except campaign_service.CampaignValidationError as exc:
        return _error(request, 422, "validation_error", "Invalid campaign", exc.fields)

    after["name"] = campaign.name
    after["description"] = campaign.description
    after["template_id"] = str(campaign.template_id) if campaign.template_id else None
    after["group_id"] = str(campaign.group_id) if campaign.group_id else None
    after["send_time"] = campaign.send_time.isoformat() if campaign.send_time else None
    after["sending_domain"] = campaign.sending_domain

    for key in ("template_id", "group_id", "send_time", "sending_domain"):
        if before[key] != after[key]:
            scope_changed = True

    if campaign.status == CampaignStatus.APPROVED and scope_changed:
        campaign_service.revoke_approved_for_scope_change(db, campaign)
        campaign.status = CampaignStatus.DRAFT
        after["status"] = campaign.status.value

    changed = {k: v for k, v in after.items() if before.get(k) != v}
    if changed:
        db.add(campaign)
        db.flush()
        _audit(
            request,
            db,
            org_id=campaign.org_id,
            actor_user_id=user.id,
            action="campaign.update",
            entity_type="campaign",
            entity_id=str(campaign.id),
            before={k: before[k] for k in changed if k in before},
            after=changed,
        )
        db.commit()
    return {"campaign": campaign_service.serialize_campaign(db, campaign)}


@router.post("/api/v1/campaigns/{campaign_id}/request-authorization")
async def request_authorization(
    campaign_id: str,
    req: AuthorizationRequest,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    campaign = _get_campaign(db, user.org_id, campaign_id)
    if campaign is None:
        return _error(request, 404, "not_found", "Campaign not found")
    org = _org(db, user.org_id)
    try:
        auth = campaign_service.request_authorization(
            db,
            org,
            campaign,
            requested_by=user.id,
            valid_from=req.valid_from,
            valid_until=req.valid_until,
            note=_clean(req.note),
        )
    except campaign_service.CampaignValidationError as exc:
        return _error(
            request, 422, "validation_error", "Campaign is not ready", exc.fields
        )
    except campaign_service.CampaignConflictError as exc:
        return _error(request, 409, exc.code, exc.message)
    _audit(
        request,
        db,
        org_id=campaign.org_id,
        actor_user_id=user.id,
        action="campaign.request_authorization",
        entity_type="campaign",
        entity_id=str(campaign.id),
        after={
            "authorization_id": str(auth.id),
            "status": campaign.status.value,
            "target_count": auth.target_count,
            "sending_domain": auth.sending_domain,
        },
    )
    db.commit()
    return {
        "campaign": campaign_service.serialize_campaign(db, campaign),
        "authorization": campaign_service.serialize_authorization(db, auth),
    }


@router.get("/api/v1/campaigns/{campaign_id}/authorizations")
async def list_campaign_authorizations(
    campaign_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
):
    campaign = _get_campaign(db, user.org_id, campaign_id)
    if campaign is None:
        return _error(request, 404, "not_found", "Campaign not found")
    rows = list(
        db.execute(
            select(Authorization)
            .where(Authorization.campaign_id == campaign.id)
            .order_by(Authorization.created_at.desc())
        ).scalars()
    )
    return {
        "authorizations": [campaign_service.serialize_authorization(db, a) for a in rows]
    }


@router.get("/api/v1/authorizations")
async def list_authorizations(
    status: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    stmt = select(Authorization).where(Authorization.org_id == user.org_id)
    if status:
        try:
            stmt = stmt.where(Authorization.status == AuthorizationStatus(status))
        except ValueError:
            return {"authorizations": [], "total": 0}
    rows = list(
        db.execute(stmt.order_by(Authorization.created_at.desc())).scalars()
    )
    return {
        "authorizations": [campaign_service.serialize_authorization(db, a) for a in rows],
        "total": len(rows),
    }


@router.post("/api/v1/authorizations/{authorization_id}/approve")
async def approve_authorization(
    authorization_id: str,
    req: ApprovalDecision,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    auth = _get_authorization(db, user.org_id, authorization_id)
    if auth is None:
        return _error(request, 404, "not_found", "Authorization not found")
    org = _org(db, user.org_id)
    try:
        campaign_service.approve_authorization(
            db, org, auth, approved_by=user.id, note=_clean(req.note)
        )
    except campaign_service.CampaignConflictError as exc:
        return _error(request, 409, exc.code, exc.message)
    _audit(
        request,
        db,
        org_id=auth.org_id,
        actor_user_id=user.id,
        action="authorization.approve",
        entity_type="authorization",
        entity_id=str(auth.id),
        after={
            "campaign_id": str(auth.campaign_id),
            "status": auth.status.value,
            "approved_by": str(user.id),
            "target_count": auth.target_count,
        },
    )
    db.commit()
    return {"authorization": campaign_service.serialize_authorization(db, auth)}


@router.post("/api/v1/authorizations/{authorization_id}/reject")
async def reject_authorization(
    authorization_id: str,
    req: RejectionDecision,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    auth = _get_authorization(db, user.org_id, authorization_id)
    if auth is None:
        return _error(request, 404, "not_found", "Authorization not found")
    org = _org(db, user.org_id)
    try:
        campaign_service.reject_authorization(
            db, org, auth, rejected_by=user.id, reason=req.reason
        )
    except campaign_service.CampaignConflictError as exc:
        return _error(request, 409, exc.code, exc.message)
    _audit(
        request,
        db,
        org_id=auth.org_id,
        actor_user_id=user.id,
        action="authorization.reject",
        entity_type="authorization",
        entity_id=str(auth.id),
        reason=req.reason,
        after={"campaign_id": str(auth.campaign_id), "status": auth.status.value},
    )
    db.commit()
    return {"authorization": campaign_service.serialize_authorization(db, auth)}


@router.post("/api/v1/campaigns/{campaign_id}/launch")
async def launch_campaign(
    campaign_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    campaign = _get_campaign(db, user.org_id, campaign_id)
    if campaign is None:
        return _error(request, 404, "not_found", "Campaign not found")
    org = _org(db, user.org_id)
    problems = campaign_service.launch_blockers(db, org, campaign)
    if problems:
        return _error(
            request,
            409,
            "authorization_required",
            "This campaign cannot be launched yet.",
            problems,
        )
    campaign.status = (
        CampaignStatus.SCHEDULED
        if campaign.send_time is None
        or campaign_service.ensure_utc(campaign.send_time) > campaign_service.utcnow()
        else CampaignStatus.RUNNING
    )
    db.add(campaign)
    db.flush()
    _audit(
        request,
        db,
        org_id=campaign.org_id,
        actor_user_id=user.id,
        action="campaign.launch",
        entity_type="campaign",
        entity_id=str(campaign.id),
        after={"status": campaign.status.value},
    )
    db.commit()
    return {"campaign": campaign_service.serialize_campaign(db, campaign)}


@router.post("/api/v1/campaigns/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    campaign = _get_campaign(db, user.org_id, campaign_id)
    if campaign is None:
        return _error(request, 404, "not_found", "Campaign not found")
    if campaign.status not in (
        CampaignStatus.APPROVED,
        CampaignStatus.SCHEDULED,
        CampaignStatus.RUNNING,
    ):
        return _error(
            request, 409, "campaign_not_pausable", "This campaign cannot be paused."
        )
    before = campaign.status.value
    campaign.status = CampaignStatus.PAUSED
    db.add(campaign)
    db.flush()
    _audit(
        request,
        db,
        org_id=campaign.org_id,
        actor_user_id=user.id,
        action="campaign.pause",
        entity_type="campaign",
        entity_id=str(campaign.id),
        before={"status": before},
        after={"status": campaign.status.value},
    )
    db.commit()
    return {"campaign": campaign_service.serialize_campaign(db, campaign)}


@router.post("/api/v1/campaigns/{campaign_id}/cancel")
async def cancel_campaign(
    campaign_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    campaign = _get_campaign(db, user.org_id, campaign_id)
    if campaign is None:
        return _error(request, 404, "not_found", "Campaign not found")
    if campaign.status in (CampaignStatus.COMPLETED, CampaignStatus.CANCELLED):
        return _error(
            request, 409, "campaign_not_cancellable", "This campaign cannot be cancelled."
        )
    before = campaign.status.value
    campaign.status = CampaignStatus.CANCELLED
    rows = list(
        db.execute(
            select(Authorization).where(
                Authorization.campaign_id == campaign.id,
                Authorization.status.in_(
                    [AuthorizationStatus.REQUESTED, AuthorizationStatus.APPROVED]
                ),
            )
        ).scalars()
    )
    for auth in rows:
        auth.status = AuthorizationStatus.REVOKED
        auth.revoked_at = campaign_service.utcnow()
        auth.reason = "Campaign cancelled."
        db.add(auth)
    db.add(campaign)
    db.flush()
    _audit(
        request,
        db,
        org_id=campaign.org_id,
        actor_user_id=user.id,
        action="campaign.cancel",
        entity_type="campaign",
        entity_id=str(campaign.id),
        before={"status": before},
        after={"status": campaign.status.value, "revoked_authorizations": len(rows)},
    )
    db.commit()
    return {"campaign": campaign_service.serialize_campaign(db, campaign)}


@router.post("/api/v1/campaigns/{campaign_id}/test-send")
async def test_send(
    campaign_id: str,
    req: TestSendRequest,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    campaign = _get_campaign(db, user.org_id, campaign_id)
    if campaign is None:
        return _error(request, 404, "not_found", "Campaign not found")
    org = _org(db, user.org_id)
    try:
        result = campaign_service.test_send(
            db, org, campaign, user=user, recipient=req.recipient
        )
    except campaign_service.CampaignValidationError as exc:
        return _error(request, 422, "validation_error", "Test send refused", exc.fields)
    except Exception:  # SMTP/sandbox failures stay non-fatal for the draft
        return _error(
            request,
            502,
            "test_send_failed",
            "The test message could not be delivered to Mailpit.",
        )
    _audit(
        request,
        db,
        org_id=campaign.org_id,
        actor_user_id=user.id,
        action="campaign.test_send",
        entity_type="campaign",
        entity_id=str(campaign.id),
        after={
            "recipient": result["recipient"],
            "sandbox": True,
            "template_id": str(campaign.template_id) if campaign.template_id else None,
        },
    )
    db.commit()
    return result
