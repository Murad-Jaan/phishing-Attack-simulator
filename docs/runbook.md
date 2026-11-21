# Operations runbook

Operate the local Docker stack only. Never point the simulator at real
recipients: delivery is restricted to Mailpit and the sandbox domains in
`.env`.

## Start, stop and status

```bash
cp .env.example .env          # first run only; then edit local values
make up                       # build and start postgres, redis, mailpit, api, worker, beat, web
docker compose ps             # service and health status
curl -fsS http://127.0.0.1:8000/health
```

Useful endpoints:

| Service | URL |
|---|---|
| Web UI | http://127.0.0.1:3000 |
| API docs | http://127.0.0.1:8000/docs |
| Mailpit | http://127.0.0.1:8025 |

```bash
docker compose stop beat      # pause scheduled dispatch only
docker compose up -d beat     # resume scheduled dispatch
docker compose down           # stop the stack, keep data
make reset                    # destructive: remove containers, volumes and data
```

## Migrations

Migrations must have exactly one head. Check and apply:

```bash
docker compose exec -T -e PYTHONPATH=/app api alembic heads
docker compose exec -T -e PYTHONPATH=/app api alembic current
make migrate                  # alembic upgrade head
```

Downgrade only in a disposable local environment:

```bash
docker compose exec -T -e PYTHONPATH=/app api alembic downgrade -1
```

## Seed data

```bash
make seed
```

Seeding is guarded by `APP_ENV=development` and refuses to overwrite an
existing organization. Demo passwords come from `.env`; do not commit them.

## Logs

```bash
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f beat
docker compose logs -f web
docker compose logs --since=30m api worker beat
```

Request IDs are returned as `X-Request-ID` and written into audit rows.

## Scheduling and dispatch

`beat` enqueues `campaigns.dispatch_due` every 30 seconds. The worker:

1. re-checks the latest authorization status and expiry;
2. compares the approved scope (group, template version, recipient count,
   domain, send time, send window, rate cap);
3. enforces the send window and hourly rate cap;
4. writes idempotent per-target rows to `campaign_sends` (one per
   campaign/target pair) and records `campaign.send_batch` or
   `campaign.send_blocked` audit events.

Manual checks:

```bash
docker compose exec -T redis redis-cli KEYS 'celery*' | head
docker compose exec -T -e PYTHONPATH=/app api celery -A app.worker.celery_app inspect ping
docker compose exec -T -e PYTHONPATH=/app api python - <<'PY'
from app.db import SessionLocal
from app.services import scheduling_service
with SessionLocal() as db:
    print(scheduling_service.dispatch_due(db))
PY
```

To pause delivery, use the campaign Pause action or `docker compose stop beat`.
Resume from the UI or `POST /api/v1/campaigns/{id}/resume` (requires an approved,
unexpired authorization and the staff role).

## Retention

Preview counts without deleting:

```bash
docker compose exec -T -e PYTHONPATH=/app api python - <<'PY'
from app.db import SessionLocal
from app.services import retention_service
with SessionLocal() as db:
    print(retention_service.preview(db, org_id=None))
PY
```

Scopes are `sessions` (fixed 7-day grace) and `campaign_sends` (organization
`retention_days`). The daily task `retention.run_scheduled` runs destructively
with counts audited as `retention.run`; it never exports row contents.
Administrators can preview through `GET /api/v1/settings/retention/preview`.

## Audit log and export

Administrators open `/settings/audit` to filter and export events. The CSV
export is `POST /api/v1/audit/export`, requires the session CSRF token, is
capped at 10,000 rows and neutralizes spreadsheet formula prefixes. The export
itself is audited as `audit.export`. The database trigger rejects updates and
deletes on `audit_log`.

## Common failures

| Symptom | Check | Fix |
|---|---|---|
| API exits on startup | `docker compose logs api` | Validate `.env` secrets; production requires strong values. |
| `alembic` has multiple heads | `alembic heads` | Resolve the duplicate revision before upgrading; never edit a committed migration. |
| Campaign create returns 500 after an upgrade | `alembic current` | Run `make migrate`. |
| Campaigns never send | `docker compose ps beat worker`; beat logs | Start `beat` and `worker`; confirm Redis health. |
| Sends blocked as `authorization_expired` | Campaign authorization status | Request a fresh authorization after the approval window ends. |
| Sends blocked as `scope_changed` | Audit event `campaign.send_blocked` | Revert the campaign to the approved scope or request a new approval. |
| Sends blocked as `send_window_closed` | Campaign send window | Extend the window and re-approve the campaign. |
| Rate-limited with zero sends | Rate cap, `campaign_sends.sent_at` | Wait for the next hourly bucket or raise the rate cap with a new approval. |
| Test send fails | `docker compose logs mailpit api` | Confirm Mailpit is healthy and the recipient is the session user or sandbox inbox. |
| Web cannot reach API | `docker compose logs web api` | Confirm `API_INTERNAL_URL=http://api:8000` and API health. |
| Login rate-limited | Redis keys `rl:acct:*`, `lock:acct:*` | Wait for the lockout or use `make unlock-user EMAIL=...`. |

## Verification before handoff

```bash
make lint
make test
```

`make test` runs the backend suite, clears local rate-limit keys, then runs the
Playwright suite with one worker. Reports are written under
`frontend/playwright-report/` and `frontend/test-results/`.
