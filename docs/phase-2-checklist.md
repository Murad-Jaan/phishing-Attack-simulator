# Phase 2 Checklist — Core Platform

Phase 2 builds the core platform only. It does **not** include event tracking, awareness, training, reports or the analyzer; those move to Phase 3/4 as defined in [`PROMPT.md`](../PROMPT.md). Legacy remains frozen.

**Phase 2 scope:** platform foundations, settings and retention, auth/sessions/CSRF/roles, groups and targets with CSV import, template library, campaign creator with authorization gate, Mailpit delivery with Celery scheduling, audit log foundation.

**Out of scope (Phase 3+):** tracking events, awareness/training, reports/trends/exports, report-phish workflow, detector workspace.

---

## Milestones

| ID | Milestone | Depends on | Size |
|---|---|---|---|
| **M0** | Foundation and developer environment | — | L |
| **M1** | Auth, sessions, CSRF, roles and audit foundation | M0 | L |
| **M2** | Org settings and retention foundation | M1 | M |
| **M3** | Groups and targets with CSV import | M2 | M |
| **M4** | Template library and versioning | M3 | M |
| **M5** | Campaign creator, test send and authorization gate | M4 | L |
| **M6** | Celery scheduling, rate caps and send window | M5 | L |

### M0 — Foundation and developer environment (L)

| Task | Size | Acceptance criteria |
|---|---|---|
| Docker Compose: `web`, `api`, `worker`, `postgres`, `redis`, `mailpit` | M | `docker compose up` starts all services; health checks defined; Mailpit UI loopback-only. |
| `.env.example` with all required variables and safe defaults | S | No secrets committed; missing required vars fail fast with a clear error. |
| `Makefile` targets (`up`, `down`, `test`, `lint`, `migrate`, `seed`) | S | Targets work from repo root; documented in README. |
| Health endpoint (`GET /health`) | S | Returns app + DB + Redis status; no auth; used by Compose health check. |
| Alembic baseline migration | S | `alembic upgrade head` on empty DB creates baseline; downgrade works. |
| Basic SMTP-to-Mailpit sending (synchronous, sandbox only) | M | Synchronous send to Mailpit loopback-only; never external; test endpoint blocked in prod; used by M5 test send. |
| CI for the new stack | M | Lint, type-check, unit tests and migration check run on PR; legacy checks still run. |
| **Frontend foundation**: Next.js + Tailwind + shadcn/ui setup | M | TypeScript, Tailwind config, shadcn/ui components; follows repo structure. |
| **Frontend foundation**: Design tokens from `docs/design-system.md` | S | CSS variables mapped from design system; light/dark tokens applied. |
| **Frontend foundation**: Single content file `src/content/en.ts` | S | All UI strings sourced from this file; glossary/copy rules followed. |
| **Frontend foundation**: App shell and navigation | M | Accessible landmarks, skip link, role-based nav, no inline scripts. |
| **Frontend foundation**: Playwright with axe-core accessibility baseline in CI | M | axe-core checks run; no serious/critical violations; CI gate. |
| **Frontend foundation**: CSP nonce approach for Next.js (no inline scripts) | M | Nonce generated per request; CSP header uses nonce; no inline scripts. |
| Dev-only seed script | S | Creates clearly labelled demo data; refuses to run when `APP_ENV=production`; excluded from real reporting. |
| Open decisions confirmed | S | Owner approved the open decisions in [`assumptions.md`](assumptions.md) (incl. T1656 verification). |

### M1 — Auth, sessions, CSRF, roles and audit foundation (L)

| Task | Size | Acceptance criteria |
|---|---|---|
| Password hashing (Argon2id) | M | Only Argon2id hashes stored; parameters documented; rehash-on-login supported. |
| Server-side sessions | M | HttpOnly + SameSite cookies; session rotation on login; logout invalidates server-side. |
| CSRF protection | M | Mutating requests require a valid CSRF token; missing/invalid token returns `403`; login protected. |
| Login rate limiting and lockout | M | Per-account and per-IP throttling; lockout with backoff; generic errors; audit entry. |
| Roles (admin, analyst, employee) | M | Server-side RBAC on every endpoint; UI hides unauthorized actions; tests for 401/403. |
| Last-admin guard | S | Cannot demote/deactivate the last active admin; clear error; test. |
| **Audit table and write helper** | M | Append-only audit table; write helper used by privileged/destructive actions; no secrets logged; tests. |
| Auth audit entries | S | Login success/failure, logout, lockout, role change recorded without secrets. |
| **Extend seed script with two clearly labelled demo admins** | S | Add `demo-admin-1` and `demo-admin-2` once users and auth exist; separation of duties (approver is not the creator) is tested with them; still refuses in production and excluded from real reporting. |
| **Frontend auth shell** | M | Login form, session handling, CSRF integration, error states accessible; strings from `src/content/en.ts`. |

**Note:** individual-detail access (admin-only with logged reason) belongs to Phase 3 reporting; the role and audit foundation is built here.

### M2 — Organization settings and retention foundation (M)

| Task | Size | Acceptance criteria |
|---|---|---|
| Organization settings | M | Name, primary domain, timezone; validation; audit on change. |
| Sandbox sending-domain allowlist | M | Only `example.com`, `*.test`, `*.invalid`; rejects real domains; admin sees warning. |
| Minimum group size setting | S | Hard floor 5; admins can raise, never lower; API rejects lower values. |
| Retention setting | S | Default 90 days, configurable; preview scope; deletion/anonymization audited. |
| Settings UI | M | Accessible form states; permission-gated; no silent failures. |
| Retention job skeleton | M | Celery task scaffold (runs in M6); idempotent; dry-run mode. |

### M3 — Groups and targets with CSV import (M)

| Task | Size | Acceptance criteria |
|---|---|---|
| Groups CRUD | M | Name, description, department; org-scoped; audit on change. |
| Targets CRUD | M | Minimal fields (email, display name); duplicate detection; no unnecessary PII. |
| CSV import | L | Template download; 5 MB limit; row-level errors; partial import keeps valid rows; formula-injection safe. |
| Suppression warning | S | Groups below 5 flagged; reports will be suppressed. |
| Import audit | S | Counts and errors recorded; no raw file retention by default. |
| Accessibility | S | Table, form and error patterns follow design system; keyboard and screen-reader checks. |

### M4 — Template library and versioning (M)

| Task | Size | Acceptance criteria |
|---|---|---|
| Template model and versioning | M | Immutable versions; draft/published; audit. |
| Template library UI | M | Search/filter, cards, preview entry point; archived read-only. |
| Red-flag metadata | M | ATT&CK ID and difficulty required; red flags shown in preview. |
| Sandbox-content validation | M | No real brands/domains; unsafe content blocked with explanation. |
| Seed templates | M | SC-01…SC-10 available as dev seeds, clearly labelled; no legacy edits. |

### M5 — Campaign creator, test send and authorization gate (L)

| Task | Size | Acceptance criteria |
|---|---|---|
| Campaign model and draft autosave | M | Server-side draft; autosave indicator; back preserves data. |
| Stepper UI (5 steps) | M | One primary action; accessible progress; exit/confirm. |
| Test send | M | Sends **only** to creator's verified address or Mailpit sandbox inbox; never target group; clearly labelled. |
| Authorization request | M | Scope, dates and sending domains bound; approver ≠ creator. |
| Authorization review | M | Approve/reject with reason; expiry; audit; scope change invalidates approval. |
| Launch guard | S | Launch disabled without valid approval; explains next step. |
| Campaign audit | S | Create, edit, test send, request/approve/reject, launch recorded. |

### M6: Celery scheduling, rate caps, send window and audit export UI (L)

| Task | Size | Acceptance criteria |
|---|---|---|
| Celery scheduling | M | Scheduled sends via worker/beat; idempotent; timezone-aware; cancel/pause. |
| Rate caps and send window | M | Server-side enforcement; authorization expiry checked at send time. |
| **Audit export and filter UI** | M | Filters + export for audit logs; RBAC-gated; append-only; no secrets. |
| Retention job | M | Runs on schedule; preview, delete/anonymize, audit; tested. |
| Operational docs | S | Runbook for start/stop, migrations, seeding, logs and common failures. |

---

## Test plan (linked to milestones)

| Test | Milestone | Type |
|---|---|---|
| Compose services healthy; health endpoint | M0 | Integration |
| `.env` validation and seed guard | M0 | Unit |
| Alembic upgrade/downgrade | M0 | Migration |
| Argon2id hashing and rehash | M1 | Unit |
| Session cookie flags, rotation, logout | M1 | Integration |
| CSRF accept/reject | M1 | Integration |
| Rate limit and lockout/backoff | M1 | Integration |
| RBAC 401/403 matrix | M1 | API |
| Last-admin guard | M1 | API |
| Settings validation + domain allowlist | M2 | API/UI |
| Group size floor 5 (raise yes, lower no) | M2 | API |
| Retention dry-run + audited deletion | M2/M6 | Integration |
| Groups/targets CRUD + duplicates | M3 | API |
| CSV row errors, partial import, formula injection | M3 | Unit/API |
| Template versioning and unsafe-content block | M4 | API/UI |
| Draft autosave and back navigation | M5 | E2E |
| Test send restricted to creator/Mailpit | M5 | Integration |
| Authorization scope binding, expiry, approver ≠ creator | M5 | API/E2E |
| Mailpit delivery and scheduling idempotency | M6 | Integration |
| Audit append-only and export | M6 | API |
| Legacy regression: `node legacy/scripts/test.js legacy/index.html` and `bash legacy/scripts/security-check.sh legacy/index.html` | all | Regression |

---

## Security gates

- [ ] No secrets committed; secret scanning green.
- [ ] Dependency scanning green.
- [ ] SAST/basic checks green.
- [ ] Secure headers and CSP configured; no inline scripts.
- [ ] Argon2id hashing only; no plaintext or weak hashes.
- [ ] Session cookies HttpOnly, SameSite, Secure in production.
- [ ] CSRF enforced on all mutating requests.
- [ ] Login rate limiting and lockout tested.
- [ ] Authorization checks on every sensitive endpoint; org scoping verified.
- [ ] Authorization gate binds scope, dates and sending domains.
- [ ] Last-admin guard tested.
- [ ] Audit coverage for privileged/destructive actions.
- [ ] Mailpit loopback-only; no real external delivery.

---

## Definition of done

- [ ] Owner approved the open decisions in [`assumptions.md`](assumptions.md).
- [ ] M0–M6 acceptance criteria met.
- [ ] Test plan green for each milestone.
- [ ] Security gates green.
- [ ] UI follows [`hci-and-wireframes.md`](hci-and-wireframes.md) and [`design-system.md`](design-system.md).
- [ ] Migrations and seed script documented and reproducible.
- [ ] No changes to `legacy/`.
- [ ] Phase 3 scope explicitly deferred (events, tracking, awareness, training, reports, report-phish).

---

## Open decisions

- [ ] **T1656 tactic**: to verify against current MITRE ATT&CK (see [`assumptions.md`](assumptions.md)).
- [x] **SSO**: deferred to Phase 5.
- [x] **Mail provider**: Mailpit only through Phase 5; any pilot SMTP relay needs a separate approved decision (docs/PLAN.md).
