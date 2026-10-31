# Backend

Python FastAPI API, PostgreSQL schema and migrations, and Celery workers for the Phishing Attack Simulator.

**Status:** Phase 2 — milestone M1 implemented: password hashing (Argon2id), server-side sessions with rotation, CSRF double-submit, login rate limiting/lockout, RBAC, last-admin guard, append-only audit, demo seed and unlock command. M2 (org settings) is next.

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

## Implemented in M1

### Auth endpoints (`app/api/v1/auth.py`)

- `GET /api/v1/auth/csrf` — issues a login token when unauthenticated, a session-bound token when a valid session cookie is present; both accepted by the double-submit check (cookie value must equal the `X-CSRF-Token` header).
- `POST /auth/login` — CSRF (login or own-session token), rate limits, Argon2id verify (dummy verify keeps timing flat for unknown users), session rotation, `HttpOnly` session cookie (`phishsim_session` dev / `__Host-phishsim_session` prod) and `HttpOnly` CSRF cookie (clients fetch fresh tokens from `/api/v1/auth/csrf`).
- `POST /auth/logout` — requires double-submit CSRF bound to the session; revokes server-side.
- `GET /auth/me` — id, email, display name, role, org id; 401 without session.

### Users (`app/api/v1/users.py`)

- `GET /api/v1/users`, `PATCH /api/v1/users/{id}` — admin-only, org-scoped; last-admin guard with `SELECT ... FOR UPDATE` on the org row returns 409 `last_admin_guard`; role changes and deactivation revoke all that user's sessions; audited.

### Operational commands

- `make seed` — creates Demo Organization (`demo-org`) and two demo admins; refuses in production; passwords from `DEMO_ADMIN_1_PASSWORD`/`DEMO_ADMIN_2_PASSWORD` (≥12 chars); idempotent (never overwrites passwords, never reactivates users).
- `make unlock-user EMAIL=...` — clears Redis lockout/failure keys for an account, writes one `user.unlock` audit row; fails clearly for unknown emails.

### Notes

- The CSRF cookie is `HttpOnly` on purpose: browser clients call `GET /api/v1/auth/csrf` for a fresh token instead of reading the cookie.
- Session tokens are only stored hashed (sha256); cookies carry the raw token, the database never does.
- Rate limiting needs Redis: if Redis is unreachable login requests fail closed with 503.
- `make migrate` before `make seed` on a fresh database.
