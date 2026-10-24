# Legacy Reference App (v1)

This directory contains the original single-file Phishing Attack Simulator, preserved **unchanged** as the reference for scenarios, detection rules, scoring and tests. It is not imported by the new stack.

## Files

```
index.html                  the whole v1 app (HTML + CSS + JavaScript)
scripts/test.js             unit tests (Node.js, no dependencies)
scripts/security-check.sh   security checks
```

## Run locally

From the repository root:

```bash
node legacy/scripts/test.js legacy/index.html
bash legacy/scripts/security-check.sh legacy/index.html
```

Or from this directory:

```bash
node scripts/test.js index.html
bash scripts/security-check.sh index.html
```

Open `index.html` in a browser to use the demo. It has no build step and makes no network requests.

## Important

- Do not change the legacy logic. Port behaviour deliberately into `frontend/`, `backend/` and `ml/` with tests.
- The Phase 1 inventory and migration decisions are in [`../docs/legacy-migration-map.md`](../docs/legacy-migration-map.md).
- The legacy CI runs from the repository root with explicit paths.
- The legacy GitHub Pages demo is deployed from this directory by `.github/workflows/pages.yml` once the repository owner switches the Pages source to GitHub Actions.
