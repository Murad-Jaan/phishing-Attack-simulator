"""Public tracking click and awareness endpoints.

These routes are deliberately unauthenticated: the unguessable per-target token
in the email is the capability. No IP address or user-agent is stored.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models.campaign import Campaign
from app.services import tracking_service

router = APIRouter()

_NO_STORE = {
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
}


def _awareness_base() -> str:
    return (
        settings.TRACKING_BASE_URL.strip().rstrip("/")
        or settings.APP_BASE_URL.strip().rstrip("/")
        or "http://127.0.0.1:3000"
    )


@router.get("/t/{token}")
def track_click(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    link = tracking_service.record_click(
        db, token, request.headers.get("user-agent")
    )
    if link is not None:
        db.commit()
    campaign = db.get(Campaign, link.campaign_id) if link is not None else None
    base = (
        tracking_service.tracking_base(campaign)
        if campaign is not None
        else _awareness_base()
    )
    location = f"{base}/learn/{quote(token, safe='')}"
    return RedirectResponse(location, status_code=302, headers=_NO_STORE)


@router.get("/api/v1/awareness/{token}")
@router.get("/awareness/{token}")
def awareness(
    token: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return {
        "simulation": True,
        "red_flags": tracking_service.awareness_red_flags(db, token),
    }
