import uuid
from typing import Any

from app.db import SessionLocal
from app.services import retention_service
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
