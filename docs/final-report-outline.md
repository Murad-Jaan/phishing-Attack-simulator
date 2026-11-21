# Final Report Outline

This outline is the structure for the final written report. It records what was built, how it was evaluated, and what remains. Figures and test counts come from the current repository and a fresh-clone run of `make demo`, `make lint` and `make test`.

## 1. Problem

- Organizations need safe, measurable phishing-awareness training and a way to explain real-email risk without collecting credentials or punishing individuals.
- Most awareness tools stop at click counts. Most mail analyzers give a score without reasons. This project joins the two: simulation results tune training and detection, and detection findings become new simulation templates.
- Scope: authorized, educational simulations; sandbox delivery; group-level reporting; explainable detection; accessible, blame-free learner experience.

## 2. Ethics and authorization

- Authorized use only. Written authorization and rules of engagement are required before a campaign can launch; the launch gate re-checks the approved scope, group, template version, recipient count, sending domain and schedule.
- Two-admin approval. A requester cannot approve their own campaign; any scope change revokes the prior approval.
- No credential capture. A simulated form records only that it was touched.
- Sandbox domains only (`example.com`, `*.test`, `*.invalid`). Mailpit is the only development destination.
- Data minimization and retention: configurable retention (default 90 days), no raw IP address or user-agent storage for tracking events, group-level reporting with small-group suppression.
- Non-punitive tone: no individual ranking, shaming or scoreboards; the awareness page is immediate, short and blame-free.
- Audit log for privileged, authorization and campaign actions.

## 3. ATT&CK framing

- **T1566.001** — spearphishing attachment: represented as template metadata and analyzer attachment checks, without real malicious attachments.
- **T1566.002** — spearphishing link: the main simulation path, with per-target tracking tokens, click events and an awareness page.
- **T1566.003** — spearphishing via service: template scenarios model service-impersonation lures.
- **T1598** — phishing for information: templates and analyzer content rules model credential and information requests.
- Kill-chain view: recon → lure design → delivery → user action → awareness → report.
- Defensive mapping: detection reasons and simulation events support training, reporting and detection tuning rather than real offensive operations.

## 4. HCI methods and accessibility results

Methods applied:

- Nielsen's 10 heuristics and Shneiderman's 8 golden rules.
- Hick's law (few choices per screen) and Fitts's law (large, close primary actions).
- Error prevention: launch checklist, test send, two-admin approval, confirmation of impact.
- Recognition over recall: template gallery, saved groups, filters, visible status.
- Explainable security: every warning states why, in plain language.
- Teachable moment: immediate awareness page, under three minutes, blame-free.

Accessibility results:

- WCAG 2.2 AA target: 4.5:1 text contrast, keyboard operation, visible focus, no color-only meaning, 44 px touch targets.
- Automated axe checks pass for public and authenticated pages in light and dark themes.
- Playwright checks keyboard skip link, logical tab order, `aria-current`, Escape/focus return for the mobile drawer, reduced motion, and 320/768/1440 px layouts.
- Known gap: no formal SUS study yet; results are automated and manual checks, not participant data.

## 5. Detection method

Layered, explainable, offline scoring:

1. **Authentication:** SPF, DKIM, DMARC, ARC results and Reply-To/From mismatch.
2. **Sender and domain:** lookalikes, homoglyphs, free-mail misuse and display-name mismatch.
3. **URLs:** display-text/href mismatch, shorteners, IP URLs, excessive subdomains, punycode and offline blocklist checks.
4. **Content:** urgency, fear, reward, generic greeting and credential requests.
5. **Attachments and HTML:** risky extensions, macro-enabled types, hidden elements and embedded forms.
6. **Output:** 0–100 score, label (Safe, Suspicious, Likely phishing), plain-language reasons and action advice.

The analyzer does not fetch live DNS/WHOIS/reputation data and does not open links. Reports store the verdict and rule IDs only, not message content. Detection rules are covered by fixtures and scenario tests.

## 6. Test summary

Run from a fresh clone in a temporary directory:

| Suite | Count | Result |
|---|---:|---|
| Backend pytest | 330 | pass |
| Frontend Playwright | 105 | pass |
| **Total** | **435** | **pass** |

Also passing:

- `make lint` — Ruff, mypy, ESLint and TypeScript (`exit 0`).
- `make test` — pytest and Playwright (`exit 0`).
- Alembic migration chain has exactly one head: `0009_analyzer_reports`.

Coverage highlights: authentication, sessions, CSRF, rate limits, RBAC, org isolation, CSV import and formula injection, campaign authorization and scope revocation, scheduling and rate caps, tracking idempotency, bot filtering, reports and suppression, analyzer API and detection rules, retention, audit append-only triggers, single-head migrations, CSP headers, seed idempotency, demo packaging, and accessibility/responsive UI checks.

## 7. Security measures

- **CSP:** production uses a nonce-based `script-src 'nonce-…' 'strict-dynamic'` policy, `style-src 'self' 'nonce-…'`, `object-src 'none'` and `base-uri 'self'`; no inline scripts, no inline style attributes and no `unsafe-inline` in production.
- **CSRF:** session-bound tokens and Origin/Referer checks on state-changing requests.
- **Rate limits:** account and IP limits on authentication, analyzer and reporting endpoints, with lockout backoff and fail-closed behavior when Redis is unavailable.
- **Audit log:** organization-scoped, redacted payloads, append-only database triggers (update/delete/truncate blocked), CSV export.
- **Sessions and passwords:** Argon2id hashing, server-side hashed session tokens, HttpOnly/SameSite cookies, idle and absolute expiry, rotation on login.
- **Other:** parameterized queries, output escaping, sandbox send-domain allowlist, SMTP header-injection checks, generic error envelopes, security headers and last-admin protection.

## 8. Limitations and future work

- **Password reset:** no self-service reset flow; administrators unlock or reset accounts.
- **Editable settings:** the settings API exists, but the UI is read-only in this milestone.
- **ML classifier:** detection is a transparent rule engine; a trained model with a held-out evaluation and model card is future work.
- **Usability study:** no formal SUS study yet; run 5–8 participants and report SUS, task success and qualitative findings.
- Additional future work: production SMTP relay with approved pilots, live reputation/DNS enrichment, more templates and localizations, and retention automation hardening.

## 9. Reproducibility

```bash
make demo   # stack, migrations, demo org, admins, templates, group, campaigns, events
make lint   # Ruff, mypy, ESLint, TypeScript
make test   # pytest + Playwright
```

Demo login emails are printed by `make demo`. Passwords are read from `.env` and are never printed. See [`../README.md`](../README.md) for the five-minute demo script, architecture diagram and screenshot checklist.
