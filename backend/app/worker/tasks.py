import uuid
from typing import Any

from app.db import SessionLocal
from app.services import retention_service, scheduling_service
from app.worker.celery_app import celery_app


@celery_app.task(name="retention.run")
def retention_run(
    dry_run: bool = True,
    force: bool = False,
    org_id: str | uuid.UUID | None = None,
) -> dict[str, Any]:
    """Run retention cleanup.

    Dry-run is the default and only counts what would be deleted. A destructive
    run requires both ``dry_run=False`` and an explicit ``force=True``. When
    ``org_id`` is omitted the task runs for every organization; passing it
    scopes the run to one organization.
    """
    if not dry_run and force is not True:
        raise ValueError("retention_run(dry_run=False) requires force=True")

    if isinstance(org_id, str):
        target_org_id = uuid.UUID(org_id) if org_id else None
    else:
        target_org_id = org_id
    with SessionLocal() as db:
        result = retention_service.run_retention(
            db,
            dry_run=dry_run,
            force=force,
            org_id=target_org_id,
        )
        if not dry_run:
            db.commit()
        return result


@celery_app.task
def ping_task():
    return "pong"


@celery_app.task(name="retention.run_scheduled")
def retention_run_scheduled() -> dict[str, Any]:
    """Destructive daily retention run, with counts audited per organization."""
    with SessionLocal() as db:
        result = retention_service.run_retention(db, dry_run=False, force=True)
        db.commit()
        return result


@celery_app.task(name="campaigns.dispatch_due")
def dispatch_due(campaign_id: str | uuid.UUID | None = None) -> dict[str, Any]:
    """Deliver due campaign batches. Safe to run repeatedly."""
    target_id = uuid.UUID(campaign_id) if isinstance(campaign_id, str) and campaign_id else campaign_id
    with SessionLocal() as db:
        result = scheduling_service.dispatch_due(
            db, campaign_id=target_id if isinstance(target_id, uuid.UUID) else None
        )
        db.commit()
        return result
