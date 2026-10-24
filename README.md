# Phishing Attack Simulator

An authorized, educational phishing simulation and real-mail detection platform. The project combines **HCI**, **Computer Graphics**, and **Cybersecurity**: safe campaigns measure behaviour, a layered analyzer explains real-email risk, and campaign findings feed back into detection and training.

> **Authorized and educational use only.** A signed authorization and rules of engagement are required before any campaign can launch. Simulations never capture real passwords, never send malware or real attachments, and never use filter-evasion techniques. Development uses Mailpit; SMTP relay is reserved for approved pilots on sandbox domains.

## Current status

**Phase 1 — planning and design.** No application code exists yet. The legacy single-file simulator is preserved unchanged in [`legacy/`](legacy/) as the behavioural and detection reference.

The authoritative scope is [`docs/PLAN.md`](docs/PLAN.md). UI and copy rules are in [`docs/design-system.md`](docs/design-system.md). Phase 1 outputs are indexed in [`docs/README.md`](docs/README.md).

## Target stack

| Layer | Technology |
|---|---|
| Frontend | Next.js (React), Tailwind CSS, shadcn/ui, Figma-based design system |
| Backend | Python FastAPI, PostgreSQL, SQLAlchemy, Alembic |
| Async | Celery + Redis |
| Mail | Mailpit for development and testing; SMTP relay only for authorized pilots |
| Detection | dnspython, tldextract, python-Levenshtein, scikit-learn, Python `email`/mail parsing |
| Dev/test | Docker Compose, pytest, Playwright, GitHub Actions |

## Repository layout

```
frontend/     Next.js application (Phase 2+)
backend/      FastAPI API, workers and database migrations (Phase 2+)
ml/           Detection rules, features, models and evaluation (Phase 4)
docs/         Plan, design system, Phase 1 analysis and decisions
legacy/       Unchanged v1 single-file app, used as the reference implementation
.github/      CI and legacy demo deployment workflows
PROMPT.md     Project context, rules and phase backlog
CHANGELOG.md  Phase-by-phase change log
```

## Legacy reference app

The v1 app remains runnable locally:

```bash
# from the repository root
node legacy/scripts/test.js legacy/index.html
bash legacy/scripts/security-check.sh legacy/index.html
```

Or open `legacy/index.html` directly in a browser. It has no build step and makes no network requests. See [`legacy/README.md`](legacy/README.md).

The legacy GitHub Pages URL changes when the demo workflow is enabled. Until the repository owner switches Pages to **GitHub Actions**, the old root URL is expected to return 404 after the `index.html` move.

## Documentation

- [`PROMPT.md`](PROMPT.md) — shared project context, rules and phase backlog
- [`docs/PLAN.md`](docs/PLAN.md) — authoritative plan: concept, safety, HCI, detection, architecture, metrics
- [`docs/design-system.md`](docs/design-system.md) — authoritative design tokens, components, status language, copy rules
- [`docs/legacy-migration-map.md`](docs/legacy-migration-map.md) — legacy inventory and migration decisions
- [`docs/requirements.md`](docs/requirements.md) — roles, user stories and MoSCoW scope
- [`docs/ethics-and-consent.md`](docs/ethics-and-consent.md) — authorization, consent, data handling and non-punitive reporting
- [`docs/threat-model.md`](docs/threat-model.md) — assets, abuse cases, ATT&CK and kill chain
- [`docs/architecture.md`](docs/architecture.md) — components, schema and API outline
- [`docs/hci-and-wireframes.md`](docs/hci-and-wireframes.md) — personas, flows, heuristics and page wireframe specs
- [`docs/assumptions.md`](docs/assumptions.md) — defaults and decisions needed
- [`docs/evaluation-plan.md`](docs/evaluation-plan.md) — human, detector and SUS evaluation
- [`docs/phase-2-checklist.md`](docs/phase-2-checklist.md) — next-phase entry criteria and tasks

## Safety, security and privacy rules

- Written authorization and rules of engagement before launch.
- Record only that a simulated form was touched; never capture credentials.
- Sandbox sending domains only (`example.com`, `*.test`, `*.invalid`); no real brand domains or logos.
- Minimal data, configurable retention (default 90 days), and deletion support.
- Audit log for privileged and campaign actions.
- Group-level reporting by default; groups below five members are suppressed.
- Non-punitive, blame-free language; no individual ranking or shaming.
- No malware, real attachments, or filter-evasion, and no real `.eml` files committed.
- All user and email content escaped; parameterized queries; hashed passwords; CSRF and rate limiting; secrets only in environment variables.

## Development workflow

Work in small steps on a branch. Phase 1 is documentation-only; do not add application code until Phase 2 is approved. Every phase must add tests, update this README and `CHANGELOG.md`, and end with a next-phase checklist.

```bash
git switch -c phase/<name> main
# make changes
node legacy/scripts/test.js legacy/index.html
bash legacy/scripts/security-check.sh legacy/index.html
git status
```

The repository owner handles commits and pushes. Do not commit or push on their behalf.

## Roadmap

1. **Phase 1 — Planning and design.** Requirements, ethics, threat model, architecture, HCI, wireframes and phase backlog.
2. **Phase 2 — Core platform.** Auth and roles, groups and targets, templates, campaign creator, authorization gate, Mailpit delivery.
3. **Phase 3 — Tracking, awareness and reports.** Event tracking, teachable-moment page, training/quiz, group-level reports, exports.
4. **Phase 4 — Detection engine and mail analyzer.** Authentication checks, domain/URL/content/attachment analysis, explainability, model evaluation.
5. **Phase 5 — Usability and evaluation.** SUS with 5–8 participants, accessibility audit, detector evaluation, fixes and final documentation.

See [`docs/phase-2-checklist.md`](docs/phase-2-checklist.md) and [`docs/evaluation-plan.md`](docs/evaluation-plan.md).

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md).

## New Stack (Phase 2 M0)

### Quick Start
1. Copy environment file: `cp .env.example .env`
2. Start all services: `make up` (or `docker compose up --build -d`)
3. Access:
   - Frontend: http://127.0.0.1:3000
   - API: http://127.0.0.1:8000
   - API Health: http://127.0.0.1:8000/health
   - Mailpit UI: http://127.0.0.1:8025

### Make Targets
- `make up` - Start all services
- `make down` - Stop and remove services  
- `make test` - Run tests
- `make lint` - Run linters
- `make migrate` - Run database migrations
- `make seed` - Run dev seed script (dev only)

### Notes
- All services bind to 127.0.0.1 only
- Postgres, Redis, SMTP (1025) are on internal network only
- Mailpit is the only mail destination
- No secrets in repo - only .env.example with placeholders
