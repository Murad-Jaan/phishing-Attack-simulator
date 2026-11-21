# Changelog

All notable changes to this project are recorded here. The project is delivered phase by phase; the repository owner performs commits and pushes.

## [Final packaging] — Demo and report

### Added

- `make demo` / `scripts/demo.sh`: starts the stack, waits for health, migrates, seeds the demo organization, admins, templates, group, campaigns and events, and prints URLs and demo login emails without printing passwords.
- `docs/final-report-outline.md`: problem, ethics, ATT&CK, HCI/accessibility, detection, test counts, security measures, limitations and future work.
- Packaging tests for the demo target, README, screenshot checklist, report outline and `.env.example`.

### Changed

- README rewritten with the five-minute demo script, Mermaid architecture diagram, run/test commands, screenshot checklist, safety rules, security measures and known limitations.
- `make test` derives the Compose network at run time so the suite works from a fresh clone in any directory.

## [Phase 1] — Planning and design

### Added

- Phase 1 documentation set under `docs/`: legacy migration map, requirements, ethics and consent, threat model, architecture, HCI and wireframes, assumptions, evaluation plan and Phase 2 checklist.
- `PROMPT.md` with shared project context, non-negotiable rules and the Phase 1–5 backlog.
- `docs/README.md` documentation index.
- `frontend/`, `backend/` and `ml/` placeholder READMEs for Phase 2+.
- `legacy/README.md` describing the unchanged reference app.
- `.github/workflows/pages.yml` to deploy the legacy demo from `legacy/` via GitHub Actions.
- `CHANGELOG.md`.

### Changed

- Moved the legacy app from the repository root into `legacy/` without changing its logic.
- Moved `doc/` to `docs/` so all documentation links resolve.
- Updated `.github/workflows/security.yml` to run legacy tests and security checks from `legacy/`.
- Reworked root `README.md` for the rebuilt project, new structure, corrected commands and documentation links.

### Notes

- No application code was written in Phase 1.
- GitHub Pages source remains a manual repository-owner action; the workflow file alone does not change GitHub settings.
- The legacy demo URL changes once Pages is switched to GitHub Actions.
