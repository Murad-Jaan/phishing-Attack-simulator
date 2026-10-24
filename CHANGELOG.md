# Changelog

All notable changes to this project are recorded here. The project is delivered phase by phase; the repository owner performs commits and pushes.

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
