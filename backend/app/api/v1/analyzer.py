from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_session, get_current_user
from app.core import csrf, rate_limit
from app.core.errors import error_payload
from app.detection import MAX_UPLOAD_BYTES, analyze_eml, analyze_paste
from app.db import get_db
from app.models.analyzer import AnalyzerReport
from app.models.organization import Organization

router = APIRouter()

ALLOWED_LABELS = {"Safe", "Suspicious", "Likely phishing"}
ALLOWED_UPLOAD_SUFFIXES = (".eml", ".txt")


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


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "on", "yes"}


class PasteRequest(BaseModel):
    model_config = {"extra": "forbid"}

    sender: str = Field(default="", max_length=320)
    subject: str = Field(default="", max_length=1_000)
    link: str = Field(default="", max_length=4_000)
    body: str = Field(default="", max_length=100_000)
    org_domain: str | None = Field(default=None, max_length=253)
    consent: bool = False


class ReportRequest(BaseModel):
    model_config = {"extra": "forbid"}

    label: str
    rule_ids: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("label")
    @classmethod
    def _label(cls, value: str) -> str:
        if value not in ALLOWED_LABELS:
            raise ValueError("Unknown verdict")
        return value

    @field_validator("rule_ids")
    @classmethod
    def _rule_ids(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for rule_id in value:
            if not isinstance(rule_id, str) or not rule_id.strip():
                raise ValueError("Rule identifiers must be strings")
            normalized = rule_id.strip().upper()
            if len(normalized) > 16:
                raise ValueError("Rule identifier is too long")
            if normalized not in cleaned:
                cleaned.append(normalized)
        return cleaned


def _rate_limit(request: Request, user) -> None:
    result = rate_limit.check_analyzer_rate_limit(request, str(user.id))
    if not result.allowed:
        raise HTTPException(
            status_code=429,
            headers={"Retry-After": str(result.retry_after or 60)},
            detail="rate_limited",
        )


@router.post("/api/v1/analyzer")
async def analyze_message(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    _rate_limit(request, user)

    org = db.get(Organization, user.org_id)
    default_org = org.primary_domain if org is not None else ""
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        if not _truthy(form.get("consent")):
            return _error(
                request,
                422,
                "validation_error",
                "Consent is required before analyzing a message",
                {"consent": "Confirm that you are authorized to analyze this message."},
            )
        upload = form.get("file")
        if upload is None or isinstance(upload, str):
            return _error(
                request,
                422,
                "validation_error",
                "An .eml file is required",
                {"file": "Choose an .eml file to analyze."},
            )
        filename = getattr(upload, "filename", "") or ""
        if filename and not filename.lower().endswith(ALLOWED_UPLOAD_SUFFIXES):
            return _error(
                request,
                422,
                "validation_error",
                "Only .eml or .txt messages can be analyzed",
                {"file": "Choose an .eml file to analyze."},
            )
        data = await upload.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            return _error(
                request,
                413,
                "file_too_large",
                "Messages must be 5 MB or smaller",
                {"file": "The uploaded file exceeds the 5 MB limit."},
            )
        org_domain = str(form.get("org_domain") or default_org)
        analysis = analyze_eml(data, org_domain=org_domain)
    else:
        try:
            payload = await request.json()
        except Exception:
            return _error(
                request, 400, "validation_error", "Invalid request body", {}
            )
        try:
            req = PasteRequest.model_validate(payload)
        except ValidationError:
            return _error(
                request, 422, "validation_error", "Invalid analyzer input", {}
            )
        if not req.consent:
            return _error(
                request,
                422,
                "validation_error",
                "Consent is required before analyzing a message",
                {"consent": "Confirm that you are authorized to analyze this message."},
            )
        analysis = analyze_paste(
            sender=req.sender,
            subject=req.subject,
            body=req.body,
            link=req.link,
            org_domain=req.org_domain or default_org,
        )

    return {"analysis": analysis.as_dict()}


@router.post("/api/v1/analyzer/report", status_code=201)
async def report_phish(
    req: ReportRequest,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    _rate_limit(request, user)

    row = AnalyzerReport(
        org_id=user.org_id,
        user_id=user.id,
        verdict=req.label,
        rule_ids=req.rule_ids,
    )
    db.add(row)
    db.flush()
    report_id = str(row.id)
    db.commit()
    return {"ok": True, "report_id": report_id}
