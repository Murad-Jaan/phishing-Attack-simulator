# Project Context, Rules and Phase Backlog

This file records the shared project context. The authoritative scope, safety rules, HCI principles, detection layers, architecture, metrics and timeline are in [`docs/PLAN.md`](docs/PLAN.md). If this file and the plan disagree, the plan wins for scope and the rules below win for non-negotiable constraints.

## Project

A full rebuild of the **Phishing Attack Simulator**: one platform with an offensive, authorized simulation half and a defensive, explainable real-mail detection half. Simulation results tune detection and training; detection findings become new simulation templates.

## Target stack

- **Frontend:** Next.js (React) + Tailwind CSS, built from the design system in [`docs/design-system.md`](docs/design-system.md) using shadcn/ui components. UI strings live in one content file.
- **Backend:** Python FastAPI, PostgreSQL, SQLAlchemy + Alembic, Celery + Redis.
- **Mail:** Mailpit for development and testing. SMTP relay only for authorized pilots on sandbox domains.
- **Detection:** dnspython, tldextract, python-Levenshtein, scikit-learn, Python `email`/mail parsing.
- **Dev/test:** Docker Compose, pytest, Playwright, GitHub Actions CI.

## Repository layout

```
/frontend  Next.js app
/backend   FastAPI, Celery workers, migrations
/ml        Detection rules, features, models, evaluation
/docs      Plan, design system, analysis, decisions
/legacy    Unchanged v1 single-file app (reference for scenarios, rules, scoring, tests)
```

The legacy app is a reference, not a dependency. Port its logic deliberately; do not copy it blindly. Its scenarios, detection rules, scoring and tests are inventoried in [`docs/legacy-migration-map.md`](docs/legacy-migration-map.md).

## Non-negotiable project rules

### Safety and ethics

- Authorized and educational use only.
- Written authorization and rules of engagement are required before any campaign can launch.
- Never capture real passwords. Record only that a simulated form was touched.
- Sandbox sending domains only (`example.com`, `*.test`, `*.invalid`); no real brand domains or logos.
- Minimal data with a retention setting (default 90 days, configurable).
- Audit log for privileged, authorization and campaign actions.
- Non-punitive tone; group-level reporting by default; groups below five members suppressed; individual detail only for admins with a logged reason.
- No malware, real attachments, or filter-evasion techniques.
- No real `.eml` files or secrets in the repository.

### Security

- Escape all user and email content.
- Parameterized queries only.
- Hashed passwords; server-side sessions with HttpOnly, SameSite cookies and CSRF protection.
- Rate limiting on authentication, analyzer and report endpoints.
- Secrets only in environment variables.
- CSRF protection, secure headers, and least-privilege access control.

### HCI and accessibility

- Apply Nielsen's 10 heuristics and Shneiderman's 8 golden rules.
- Use Hick's law (few choices per screen) and Fitts's law (large, close primary actions).
- WCAG 2.2 AA: 4.5:1 text contrast, full keyboard use, visible focus, no color-only meaning.
- Explainable security: every warning says why, in plain language.
- Teachable moment under three minutes, immediate, blame-free.

### Delivery

- Work phase by phase in small steps on a branch.
- Show the plan and wait for approval before writing files.
- Add tests for everything that can be tested.
- End each phase with: what changed, how to run/test it, updated README/changelog, and a checklist for the next phase.
- The repository owner handles commits and pushes.

## Phase backlog

### Phase 1 — Planning and design (documentation only)

- Legacy inventory and migration map.
- Roles, user stories and MoSCoW scope.
- Ethics: rules of engagement, consent, data handling, non-punitive reporting.
- Threat model, abuse cases, ATT&CK mapping and kill chain.
- Architecture, database schema and API outline.
- HCI: personas, flows, heuristic checklists, accessibility, wireframes and states.
- Assumptions and evaluation plan.
- Phase 2 checklist.

**Exit:** all documents reviewed and accepted; no application code.

### Phase 2 — Core platform

- Organization settings and retention.
- Authentication, sessions, CSRF and roles (admin, analyst, employee).
- Groups and targets with CSV import and row-level errors.
- Template library and versioning.
- Campaign creator with draft autosave, test send, authorization gate and review.
- Mailpit delivery and campaign scheduling through Celery.
- Audit log foundation.
- Tests: pytest, Playwright, accessibility baseline.

### Phase 3 — Tracking, awareness and reports

- Event tracking: sent, opened, clicked, form touched, answered, reported.
- Teachable-moment awareness page.
- Training and quiz with explanations.
- Group-level reports, trends, department comparison and exports.
- Report-phish flow and IT triage.
- Accessibility and usability fixes.

### Phase 4 — Detection engine and mail analyzer

- Authentication checks: SPF, DKIM, DMARC, ARC, Reply-To.
- Sender/domain checks: lookalikes, homoglyphs, free-mail misuse, domain age where available.
- URL analysis: display mismatch, shorteners, IP URLs, subdomains, punycode, offline blocklist.
- Content baseline (TF-IDF + logistic regression) and transparent rule reasons.
- Attachment and HTML checks.
- Analyzer UI with 0–100 score, label and "why was this flagged?".
- Held-out evaluation, precision/recall/F1/false-positive rate and model card.

### Phase 5 — Usability and evaluation

- SUS study with 5–8 participants.
- Accessibility audit (axe-core plus manual keyboard/zoom checks).
- Detector evaluation and threshold review.
- Fixes, documentation, demo and final report.
