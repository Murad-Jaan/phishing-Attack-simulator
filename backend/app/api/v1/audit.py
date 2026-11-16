from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_session, require_admin
from app.core import csrf
from app.core.audit import write_audit
from app.db import get_db
from app.models import AuditLog, User

router = APIRouter()

MAX_EXPORT_ROWS = 10_000


class AuditExportRequest(BaseModel):
    model_config = {"extra": "forbid"}

    action: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    actor_user_id: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


def _filters(
    *,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_user_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[Any]:
    clauses: list[Any] = []
    if action:
        clauses.append(AuditLog.action.startswith(action.strip()))
    if entity_type:
        clauses.append(AuditLog.entity_type == entity_type.strip())
    if entity_id:
        clauses.append(AuditLog.entity_id == entity_id.strip())
    if actor_user_id:
        try:
            clauses.append(AuditLog.actor_user_id == uuid.UUID(actor_user_id))
        except ValueError:
            clauses.append(AuditLog.actor_user_id == uuid.uuid4())
    if date_from is not None:
        clauses.append(AuditLog.created_at >= date_from)
    if date_to is not None:
        clauses.append(AuditLog.created_at <= date_to)
    return clauses


def _serialize(row: AuditLog, email: str | None) -> dict[str, Any]:
    return {
        "id": row.id,
        "action": row.action,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "actor_user_id": str(row.actor_user_id) if row.actor_user_id else None,
        "actor_email": email,
        "reason": row.reason,
        "request_id": row.request_id,
        "before": row.before,
        "after": row.after,
        "created_at": row.created_at.isoformat(),
    }


@router.get("/api/v1/audit")
async def list_audit(
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_user_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    clauses = _filters(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        date_from=date_from,
        date_to=date_to,
    )
    stmt = (
        select(AuditLog, User.email)
        .outerjoin(User, User.id == AuditLog.actor_user_id)
        .where(AuditLog.org_id == user.org_id, *clauses)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = list(db.execute(stmt).all())
    total = int(
        db.execute(
            select(func.count(AuditLog.id)).where(
                AuditLog.org_id == user.org_id, *clauses
            )
        ).scalar_one()
    )
    return {
        "events": [_serialize(row, email) for row, email in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def _csv_cell(value: Any) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = text.replace("\r", " ").replace("\n", " ")
    if text[:1] in ("=", "+", "-", "@", "\t"):
        return "'" + text
    return text


@router.post("/api/v1/audit/export")
async def export_audit(
    req: AuditExportRequest,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
    sess=Depends(get_current_session),
):
    csrf.assert_session_csrf(request, str(sess.id))
    clauses = _filters(
        action=req.action,
        entity_type=req.entity_type,
        entity_id=req.entity_id,
        actor_user_id=req.actor_user_id,
        date_from=req.date_from,
        date_to=req.date_to,
    )
    rows = list(
        db.execute(
            select(AuditLog, User.email)
            .outerjoin(User, User.id == AuditLog.actor_user_id)
            .where(AuditLog.org_id == user.org_id, *clauses)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(MAX_EXPORT_ROWS)
        ).all()
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "created_at",
            "action",
            "entity_type",
            "entity_id",
            "actor_user_id",
            "actor_email",
            "reason",
            "request_id",
            "before",
            "after",
        ]
    )
    for row, email in rows:
        writer.writerow(
            [
                _csv_cell(row.created_at.isoformat()),
                _csv_cell(row.action),
                _csv_cell(row.entity_type),
                _csv_cell(row.entity_id),
                _csv_cell(str(row.actor_user_id) if row.actor_user_id else None),
                _csv_cell(email),
                _csv_cell(row.reason),
                _csv_cell(row.request_id),
                _csv_cell(row.before),
                _csv_cell(row.after),
            ]
        )

    write_audit(
        db,
        org_id=user.org_id,
        actor_user_id=user.id,
        action="audit.export",
        entity_type="audit",
        entity_id=None,
        after={"rows": len(rows), "format": "csv"},
        request_id=getattr(request.state, "request_id", None),
        ip=getattr(request.state, "client_ip", None),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue().encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="audit-log.csv"'},
    )
