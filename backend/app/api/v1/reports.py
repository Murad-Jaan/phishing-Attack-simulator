"""Authenticated reporting, dashboard and CSV evidence export."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_session, get_current_user, require_staff
from app.core import csrf
from app.core.audit import write_audit
from app.db import get_db
from app.models.organization import Organization
from app.services import reports_service

router = APIRouter()


class ReportExportRequest(BaseModel):
    campaign_id: str | None = None


def _org(db: Session, org_id) -> Organization:
    org = db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="organization_not_found")
    return org


@router.get("/api/v1/dashboard")
@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    org = _org(db, user.org_id)
    return reports_service.dashboard(db, org)


@router.get("/api/v1/reports/campaigns")
@router.get("/reports/campaigns")
def report_campaigns(
    db: Session = Depends(get_db),
    user=Depends(require_staff),
) -> dict[str, Any]:
    org = _org(db, user.org_id)
    campaigns = reports_service.list_campaigns(db, org.id, org.min_group_size)
    return {"campaigns": campaigns, "total": len(campaigns)}


@router.get("/api/v1/reports/summary")
@router.get("/reports/summary")
def report_summary(
    campaign_id: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
) -> dict[str, Any]:
    org = _org(db, user.org_id)
    data = reports_service.campaign_summary(db, org, campaign_id)
    if data is None:
        raise HTTPException(status_code=404, detail="campaign_not_found")
    return data


@router.post("/api/v1/reports/export")
@router.post("/reports/export")
def export_report(
    request: Request,
    req: ReportExportRequest,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
    sess=Depends(get_current_session),
) -> StreamingResponse:
    csrf.assert_session_csrf(request, str(sess.id))
    org = _org(db, user.org_id)
    data = reports_service.campaign_summary(db, org, req.campaign_id)
    if data is None:
        raise HTTPException(status_code=404, detail="campaign_not_found")
    body = reports_service.export_csv(data)

    write_audit(
        db,
        org_id=user.org_id,
        actor_user_id=user.id,
        action="report.export",
        entity_type="report",
        entity_id=req.campaign_id,
        after={
            "campaign_id": req.campaign_id,
            "suppressed": data["suppressed"],
            "groups": len(data["groups"]),
            "format": "csv",
        },
        request_id=getattr(request.state, "request_id", None),
        ip=getattr(request.state, "client_ip", None),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()

    return StreamingResponse(
        iter([body.encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="campaign-report.csv"'},
    )
