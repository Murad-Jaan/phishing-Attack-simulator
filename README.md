# Phishing Attack Simulator

A web-based cybersecurity awareness project for IT/Security departments. It runs safe, simulated phishing campaigns, trains employees with instant feedback, and detects phishing in real emails you provide.
University project combining **HCI**, **Computer Graphics** and **Cybersecurity**.

> **Educational use only.** Simulated content only. No real credentials are collected, no real emails are sent, and the page makes no network requests.

## Features
- **IT Dashboard:** create campaigns by department and difficulty; see emails sent, clicks, reports, correct/incorrect answers, detection, click and reporting rates; department and employee awareness scores (charts); employees who need training; campaign history; recommended prevention actions; **Export CSV**.
- **Employee view:** email-style inbox, mark *Phishing / Legitimate / Report*, simulated link and attachment clicks, fake login page demo (disabled inputs), instant feedback with reasons, and prevention tips.
- **Detection:** rule-based risk analyzer (sender, links, urgency, credentials, attachments) and a **real email checker** (SPF/DKIM/DMARC, Reply-To mismatch, deceptive links, risky attachments) for emails pasted from Gmail "Show original" or uploaded as `.eml`.
- **Prevention:** layered-defence guide, safe-habits checklist, and a "What to do" list for each analysed email.
- **Phishing attack visualization:** animated 5-step attack flow with the defence for each step (respects reduced-motion settings).

## Run it
No install or build step. Open `index.html` in a browser.
To publish: GitHub **Settings > Pages > Deploy from branch > main**.

## Project structure
```
index.html                      the whole app (HTML + CSS + JavaScript)
scripts/test.js                 unit tests (Node.js, no dependencies)
scripts/security-check.sh       security checks
.github/workflows/security.yml  CI: tests + security checks + CodeQL + gitleaks
.gitignore                      blocks secrets and real .eml files
```

## Development workflow
```bash
node scripts/test.js index.html            # run unit tests
bash scripts/security-check.sh index.html  # run security checks

git checkout -b feature/my-change          # work on a branch
# ...edit index.html...
git add . && git commit -m "Describe the change"
git push -u origin feature/my-change       # open a pull request; CI must pass, then merge
```

### Rules for every change
1. Any text from users or emails must go through `esc()` before it is put in `innerHTML`.
2. No network calls, external scripts, `eval`, or enabled password fields (the security check enforces this).
3. Never commit real emails (`.eml`), passwords, tokens or keys.
4. Add or update a test in `scripts/test.js` when you change a detection rule or scoring.

### Where things are in `index.html`
| Part | Function(s) |
|---|---|
| Sample data | `EMP` (employees), `SC` (simulated emails) |
| Scoring and stats | `score()`, `stats()`, `ok()`, `dpPanel()` |
| Detection | `scan()` (rules), `analyze()`, `emlText()` (real email parser) |
| Screens | `it()` dashboard, `emp()` inbox, `dp()` detect and prevent, `tips()` + `attack()` |
| Actions | `newCamp()`, `simulate()`, `answer()`, `exportCsv()` |

## GitHub settings to turn on (once)
**Settings > Code security:** Dependabot alerts, secret scanning with push protection, code scanning.
**Settings > Branches:** protect `main` (require a pull request and passing checks).
Turn on two-factor authentication for your account.

## Security design
- Content-Security-Policy `default-src 'none'`: the page cannot send data anywhere.
- Real emails are analysed only in your browser and are never stored.
- CSV export neutralises spreadsheet formula injection.
- Uploaded files are limited to 5 MB and pasted text to 2 MB.

**Known limitations:** the CSP must allow inline scripts (single-file app); detection is rule-based and can miss new attacks or flag safe emails; the IT/Employee views are a demo without real login; the `.eml` parser does not handle every MIME format.

## Roadmap
- [ ] Usability test with 5 users and record results (HCI)
- [ ] Custom scenario editor for IT admins
- [ ] Awareness trend chart across campaigns
- [ ] More scenarios (QR-code and SMS phishing)
- [ ] Split JavaScript and CSS into separate files and tighten the CSP
- [ ] Login and roles (IT admin / employee) with a backend and database
- [ ] Real-time Gmail/Outlook detection (OAuth + backend + provider API)

## Changelog
- **v1.0** Simulator, IT dashboard, detection, prevention, real-email checker, attack visualization, CSV export, tests, CI.
