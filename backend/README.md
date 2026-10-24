# Backend

Python FastAPI API, PostgreSQL schema and migrations, and Celery workers for the Phishing Attack Simulator.

**Status:** Phase 2+ — not implemented. Phase 1 is documentation-only.

## Rules

- Server-side sessions with HttpOnly, SameSite cookies and CSRF protection. No tokens in browser storage.
- Parameterized queries through SQLAlchemy; no string-built SQL.
- Passwords hashed with a modern memory-hard algorithm (Argon2id preferred; bcrypt acceptable).
- Authorization before every campaign launch; separation of duties between creator and approver.
- Record only `form_touched` for simulated form interaction. Never store field values or passwords.
- Minimal data and retention enforcement (default 90 days, configurable).
- Group-level reporting by default; suppress groups below five members; individual detail only for admins with a logged reason.
- Audit all privileged, authorization and campaign actions.
- Secrets only from environment variables. Never log secrets or raw email content.
- Escape or sanitize all user and email content before rendering or export.
- Rate-limit authentication, analyzer and report endpoints.

## Planned structure

```
app/
  api/            versioned routers
  core/           settings, security, sessions, CSRF, rate limits
  models/         SQLAlchemy models
  schemas/        Pydantic request/response models
  services/       campaigns, authorization, events, reports, retention
  workers/        Celery tasks and schedules
  detection/      adapter to the ml package (or shared library)
alembic/          migrations
tests/            pytest unit, integration and API tests
```

## Documentation

Start with [`../docs/architecture.md`](../docs/architecture.md), [`../docs/ethics-and-consent.md`](../docs/ethics-and-consent.md) and [`../docs/threat-model.md`](../docs/threat-model.md).
