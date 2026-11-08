"""Retention scope registry and execution.

Sessions are authentication artifacts, not organization data. They deliberately
use a short, fixed cleanup rule: expired or revoked sessions are kept for a
7-day grace period, then deleted. The organization's configurable
``retention_days`` setting does **not** apply to sessions; it will govern
campaign, event, report and analyzer scopes added in M3+.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.models.organization import Organization
from app.models.session import AuthSession
from app.models.user import User

# Fixed grace period for authentication sessions. Do not replace this with
# organization.retention_days: session cleanup is intentionally short and
# independent of tenant data-retention policy.
SESSION_RETENTION_GRACE_DAYS = 7


@dataclass(frozen=True)
class RetentionScope:
    """One independently counted/deleted retention scope."""

    name: str
    count: Callable[[Session, uuid.UUID, datetime], int]
    delete: Callable[[Session, uuid.UUID, datetime], int]


def _session_cutoff(now: datetime) -> datetime:
    return now - timedelta(days=SESSION_RETENTION_GRACE_DAYS)


def _session_predicate(org_id: uuid.UUID, cutoff: datetime):
    return (
        AuthSession.user_id.in_(select(User.id).where(User.org_id == org_id)),
        or_(
            AuthSession.expires_at < cutoff,
            AuthSession.revoked_at < cutoff,
        ),
    )


def _count_sessions(db: Session, org_id: uuid.UUID, now: datetime) -> int:
    cutoff = _session_cutoff(now)
    stmt = select(func.count(AuthSession.id)).where(*_session_predicate(org_id, cutoff))
    return int(db.execute(stmt).scalar_one())


def _delete_sessions(db: Session, org_id: uuid.UUID, now: datetime) -> int:
    cutoff = _session_cutoff(now)
    stmt = (
        delete(AuthSession)
        .where(*_session_predicate(org_id, cutoff))
        .execution_options(synchronize_session=False)
    )
    result = db.execute(stmt)
    return int(result.rowcount or 0)


RETENTION_SCOPES: dict[str, RetentionScope] = {
    "sessions": RetentionScope(
        name="sessions",
        count=_count_sessions,
        delete=_delete_sessions,
    ),
}
# Convenience alias for callers that just want the registry.
SCOPES = RETENTION_SCOPES


def preview(
    db: Session, *, org_id: uuid.UUID, now: datetime | None = None
) -> dict[str, int]:
    """Return counts per scope for one organization without deleting anything."""
    reference = now or datetime.now(timezone.utc)
    return {
        name: scope.count(db, org_id, reference)
        for name, scope in RETENTION_SCOPES.items()
    }


def run_retention(
    db: Session,
    *,
    dry_run: bool = True,
    force: bool = False,
    now: datetime | None = None,
    org_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Count or delete expired data for one organization or all organizations.

    ``dry_run=False`` is destructive and is refused unless ``force=True`` is
    explicitly supplied. A real run writes one audit row per organization; the
    payload contains counts only. Re-running after a successful cleanup
    deletes zero rows and records zero counts, so data cleanup stays idempotent.
    """
    if not dry_run and force is not True:
        raise ValueError("retention_run(dry_run=False) requires force=True")

    reference = now or datetime.now(timezone.utc)
    totals = {name: 0 for name in RETENTION_SCOPES}
    if org_id is not None:
        org_ids = [org_id]
    else:
        org_ids = list(db.execute(select(Organization.id)).scalars().all())

    for current_org_id in org_ids:
        org_counts: dict[str, int] = {}
        for name, scope in RETENTION_SCOPES.items():
            if dry_run:
                org_counts[name] = scope.count(db, current_org_id, reference)
            else:
                org_counts[name] = scope.delete(db, current_org_id, reference)
            totals[name] += org_counts[name]

        if not dry_run:
            write_audit(
                db,
                org_id=current_org_id,
                actor_user_id=None,
                action="retention.run",
                entity_type="retention",
                after=org_counts,
                reason="system",
            )

    return {"dry_run": dry_run, "counts": totals}
