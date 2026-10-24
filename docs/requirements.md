# Requirements

Scope source: [`PLAN.md`](PLAN.md). Design constraints: [`design-system.md`](design-system.md). Defaults and open decisions: [`assumptions.md`](assumptions.md).

This document defines what Phase 2–5 must deliver. Phase 1 delivers only this specification and the supporting design documents.

---

## 1. Roles and permissions

| Role | Purpose | Default access |
|---|---|---|
| **Admin** | Runs the platform for one organization | Organization settings, users/roles, authorizations, all campaigns, group reports, individual detail with logged reason, audit log, retention/deletion, exports |
| **Analyst** | Designs and operates simulations and triage | Templates, groups/targets, campaign drafts, authorization requests, group reports, analyzer, report triage, exports; cannot approve authorizations or view individual detail |
| **Employee** | Receives simulations and learns | Own awareness/training, report phish, own learning history; no access to other people or campaign management |
| **System** | Scheduled jobs, not a login | Delivery, event ingestion, retention, aggregation, model scoring |

### 1.1 Permission matrix

| Capability | Admin | Analyst | Employee |
|---|---|---|---|
| Sign in / sign out / manage own session | Yes | Yes | Yes |
| Manage users and roles | Yes | No | No |
| Manage organization settings and retention | Yes | No | No |
| Create/edit/archive templates | Yes | Yes | No |
| Create/edit groups and targets | Yes | Yes | No |
| Import targets by CSV | Yes | Yes | No |
| Request campaign authorization | Yes | Yes | No |
| Approve/reject/revoke authorization | Yes | No | No |
| Approve own campaign | **No** (separation of duties) | **No** | No |
| Create/schedule/edit campaign drafts | Yes | Yes | No |
| Launch/pause/cancel campaign | Yes, with approved authorization | Launch only with approved authorization; pause own campaign | No |
| View group-level reports | Yes | Yes | No |
| View individual target detail | Yes, logged reason | No | No |
| Export reports/events | Yes, audited | Yes, group-level only, audited | No |
| Run mail analyzer | Yes | Yes | No |
| Triage reported phish | Yes | Yes | No |
| View audit log | Yes | No | No |
| Delete campaign/target data | Yes, audited | No | No |
| Complete training / report phish | Yes | Yes | Yes |
| View own learning history | Yes | Yes | Yes |

**Rules**
- A campaign cannot leave `draft` or `awaiting_authorization` without an `approved` authorization covering the same campaigns, groups, templates, dates and domains.
- The authorization approver must be an admin who is not the campaign creator.
- Individual detail is never shown by default. Every drill-down requires a reason and writes an audit entry.
- Groups with fewer than five targets are suppressed in reports (default; see assumptions).
- All privileged, authorization, export and deletion actions are audited.

---

## 2. User stories and acceptance criteria

### Authentication and account

**US-AUTH-01 — Sign in**
As a registered user, I want to sign in securely so that I can reach my role's workspace.
- Given valid credentials, when I sign in, then a server-side session is created with an HttpOnly, `SameSite=Lax`/`Strict` cookie and I land on my role home.
- Given invalid credentials, when I submit, then I see a non-enumerating error ("Email or password is incorrect") and the attempt is rate-limited.
- Given five failed attempts in the window, then further attempts are throttled and the event is logged.
- The form supports password reveal, keyboard submission, visible labels and a password-manager-friendly autocomplete.

**US-AUTH-02 — Sign out**
As a signed-in user, I want to sign out so that shared devices are safe.
- Signing out revokes the server-side session and clears the cookie.
- Back-button navigation does not reveal authenticated pages.

**US-AUTH-03 — Session expiry**
As a user, I want a warning before my session expires so that I do not lose work.
- A warning appears before expiry with an option to extend.
- Draft campaign work is preserved server-side.

### Admin

**US-ADM-01 — Configure organization**
As an admin, I want to set the organization name, sender domain(s), retention period and reporting threshold so that the platform matches policy.
- Only reserved sandbox domains are accepted for simulation sending (`example.com`, `*.test`, `*.invalid`) in development; pilot relay domains require an approved authorization.
- Retention is 90 days by default and configurable within allowed bounds.
- Changes are audited.

**US-ADM-02 — Manage users and roles**
As an admin, I want to invite, deactivate and change roles so that access is least-privilege.
- Role changes take effect on the next request.
- Deactivation revokes active sessions.
- An admin cannot demote or deactivate the last active admin.

**US-ADM-03 — Review audit log**
As an admin, I want a filterable audit log so that I can investigate misuse.
- Entries include actor, action, entity, timestamp, request ID and redacted before/after values.
- Secrets, passwords and raw email content are never logged.
- Export is audited.

**US-ADM-04 — Delete data**
As an admin, I want to delete campaign or target data so that retention policy is honoured.
- Deletion requires typed confirmation naming the scope.
- A scheduled or immediate hard-delete runs and is audited.
- Aggregate reports retain no re-identifiable detail after deletion.

### Analyst — templates and groups

**US-TPL-01 — Browse templates**
As an analyst, I want a searchable template library with previews so that I can choose an appropriate simulation.
- Each card shows name, difficulty, ATT&CK technique, red-flag count and status.
- Filters cover difficulty, technique, status and language.
- Empty, loading and error states are defined.
- Preview shows desktop and mobile rendering plus a red-flag toggle.

**US-TPL-02 — Create or edit a template**
As an analyst, I want to create a realistic but safe simulation so that training matches current threats.
- Required fields: name, difficulty, ATT&CK technique, sender name/address, subject, body, red flags.
- Sender domains are restricted to the organization's approved sandbox list.
- No real brand logos, real credentials, malware or real attachments are accepted.
- Saving creates a version; editing an in-use template requires a new version.
- Validation errors are field-linked and preserve input.

**US-GRP-01 — Create a group**
As an analyst, I want named target groups so that campaigns can be scoped.
- A group has a name, description and targets.
- Duplicate target emails within an organization are rejected or merged with a clear message.
- Groups below five targets show a suppression warning before campaign creation.

**US-GRP-02 — Import targets by CSV**
As an analyst, I want to bulk-import targets so that setup is fast.
- Required columns: email, display name; optional: department, external ID.
- Row-level errors identify row number, column and reason (for example "Row 7: invalid email `ali@company`").
- Valid rows can be imported while invalid rows are corrected and re-uploaded.
- Import is limited in size, rate-limited, audited and never logs full file contents.
- Formula-injection content is neutralized on export, not trusted on import.

### Analyst — campaign and authorization

**US-CMP-01 — Create a campaign draft**
As an analyst, I want a guided campaign creator so that I do not miss safety steps.
- A five-step stepper covers template, group, schedule, review and launch.
- Draft autosaves; going back preserves input; cancel offers discard confirmation.
- One primary action per step.
- Target count and group-suppression status are visible before launch.

**US-CMP-02 — Test send**
As an analyst, I want to send a test to myself so that I can verify rendering.
- Test send uses the same rendering path and is clearly marked as a test.
- Test sends are excluded from campaign metrics.
- The test recipient must be an authenticated internal address.

**US-CMP-03 — Request authorization**
As an analyst, I want to request authorization so that launch is compliant.
- The request captures campaign scope, groups, templates, dates, sending domains, data collected, emergency contact and rules-of-engagement version.
- The campaign cannot be scheduled or launched until an admin approves.
- Changes to scope invalidate the approval and require re-approval.
- A campaign cannot be approved by its creator.

**US-CMP-04 — Schedule and launch**
As an authorized analyst, I want to schedule delivery so that the campaign runs at the right time.
- Launch shows a confirmation naming impact ("Send to 120 people in Finance on 12 Nov at 10:00?").
- A launch checklist covers authorization, sandbox domain, test send, target count and retention.
- Queued, sent, paused, cancelled and completed states are visible and audited.
- Pause stops further sends; cancel stops sends and marks the campaign closed.

**US-CMP-05 — Pause, resume and cancel**
As an operator, I want control over a running campaign so that I can stop safely.
- Pause takes effect for unsent messages within one scheduling tick.
- Resume requires the authorization to still be valid.
- Cancel requires confirmation and cannot be undone.

### Employee

**US-EMP-01 — Receive and open a simulation**
As an employee, I want the simulation to be realistic so that the practice is meaningful.
- The message arrives through the configured delivery path with a per-target tokenized link.
- Opening and clicking are recorded as events with minimal metadata.
- The experience never asks for or stores a password; a simulated form touch records only that it was touched.

**US-EMP-02 — See the teachable moment**
As an employee, I want immediate, blame-free feedback so that I learn without embarrassment.
- After a click or form touch, the awareness page appears immediately and takes under three minutes.
- It says no harm was done, no information was saved and lists the red flags with icons and text.
- It offers three tips and a "Start 3-minute training" action.
- Tone is non-punitive; there is no scoreboard or shaming.

**US-EMP-03 — Complete training**
As an employee, I want a short quiz with explanations so that I remember the signs.
- Progress is visible; each answer explains why it is right or wrong.
- Retry is allowed; completion is recorded without ranking against colleagues.
- Exiting and returning preserves progress for the session.

**US-EMP-04 — Report a suspicious message**
As an employee, I want one-click reporting so that I can ask for help safely.
- The report action is reachable from the message and the awareness page.
- A thank-you message confirms receipt and says what happens next.
- Reporting is never treated as a failure; reports feed triage and detection.
- IT triage shows status (new, triaged, confirmed, closed) to authorized roles only.

### Analyst — reports

**US-RPT-01 — View campaign results**
As an analyst, I want group-level results so that I can improve training without shaming people.
- Dashboard shows sent, delivered, opened, clicked, form touched, reported and answered.
- Rates are shown with denominators and definitions.
- Groups below five members are suppressed.
- Charts always have a table or text alternative.
- Filters cover campaign, group, date range and difficulty.

**US-RPT-02 — Compare trends**
As an analyst, I want trend and department comparison so that I can target training.
- Trends show click, report and repeat-clicker metrics over time.
- Comparisons are group-level only.
- Statistical caveats are shown (small samples, voluntary reporting).

**US-RPT-03 — Export results**
As an authorized user, I want a CSV export so that I can analyze offline.
- Export is role-limited and audited.
- CSV values that begin with `= + - @` are prefixed with `'`.
- No credentials or raw email content are included.
- Individual rows are excluded for users without individual-detail permission.

### Detection

**US-DET-01 — Analyze a pasted email**
As an analyst, I want to paste sender, link and text so that I can score a suspicious message.
- Required input: sender; optional: link, subject/body, attachment names.
- The result includes a 0–100 score, label, rule reasons and "What to do".
- Analysis is rate-limited; input size is bounded; content is not stored by default.
- The user must acknowledge that they are authorized to analyze the message.

**US-DET-02 — Upload an `.eml`**
As an analyst, I want to upload an `.eml` so that headers and links are checked.
- Max 5 MB; MIME type and extension checked; parsing is sandboxed and never executes attachments.
- The result separates header checks, content checks, link destinations and actions.
- Raw message content is not retained by default; only score, label, rule IDs and timestamp are stored.
- Malformed MIME produces a helpful error, not a crash.

**US-DET-03 — Understand why**
As a user, I want plain-language reasons so that I can trust and learn from the verdict.
- Every reason names the rule, the evidence (for example the actual domain) and the risk contribution.
- Labels are consistent: Low risk, Suspicious, Likely phishing.
- Colors are never the only signal; icon and text accompany them.
- The panel offers "Was this helpful?" feedback without storing the raw message.

**US-DET-04 — Know what to do**
As a user, I want next steps so that I can act safely.
- High risk: do not click/open/reply; report; change password and enable MFA if already interacted; block sender.
- Suspicious: verify through a known channel; check links; report if unsure.
- Low risk: no strong flags, still verify links and keep MFA.

**US-DET-05 — Report a real phish**
As an employee or analyst, I want to submit a suspicious email so that IT can triage it.
- Submission stores only approved metadata and the reporter's note.
- IT triage can mark confirmed, close as benign or escalate.
- Reporter sees a status without exposing other reporters.

### Reporting and operations

**US-OPS-01 — Retention**
As an admin, I want automatic retention so that data does not live forever.
- Data older than the configured retention is deleted or irreversibly anonymized by a scheduled job.
- Deletion is verified and audited.
- Retention applies to events, reports, analyzer runs and audit entries as defined in the data policy.

**US-OPS-02 — Audit**
As an admin, I want a tamper-evident audit trail so that misuse can be investigated.
- Audit entries are append-only for application users.
- Sensitive values are redacted.
- Export is audited.

**US-OPS-03 — Accessibility**
As a user with a disability, I want to use the platform with assistive technology.
- All pages pass WCAG 2.2 AA automated checks (no serious/critical axe issues) and manual keyboard review.
- Works at 320px width and 200% zoom.
- Focus is visible and never trapped.
- Errors are announced and linked to fields.
- Reduced-motion preferences are respected.

---

## 3. MoSCoW scope

### 3.1 Simulation module

| Priority | Requirement |
|---|---|
| **Must** | Roles and server-side sessions; organization settings; groups and targets; CSV import with row-level errors; template library; campaign creator; authorization gate with separation of duties; Mailpit delivery; scheduling; sent/clicked/form_touched/answered/reported events; awareness page; group-level reports; retention; audit; non-punitive copy |
| **Should** | Test send; draft autosave; pause/resume/cancel; template preview desktop/mobile; red-flag toggle; trend and department comparison; CSV export; training quiz; report-phish triage; email notifications for approvals |
| **Could** | Custom scenario editor; QR/SMS simulations; additional languages (for example Urdu); SSO/SAML; Slack/Teams notifications; scheduled training reminders |
| **Won't (this release)** | Real credential capture; malware or real attachments; filter evasion; real brand impersonation; public leaderboards; automated discipline; open tracking pixels; sending from non-sandbox domains without pilot approval |

### 3.2 Detection module

| Priority | Requirement |
|---|---|
| **Must** | Paste and `.eml` upload; SPF/DKIM/DMARC plus Reply-To checks; sender/domain rules; URL rules; content rules; attachment checks; 0–100 score with label; plain-language reasons; "What to do"; consent notice; rate limits; no raw-content retention by default |
| **Should** | TF-IDF + logistic-regression baseline; offline blocklist; homoglyph/punycode detection; tldextract domain normalization; model/rule versioning; feedback capture; held-out evaluation report; per-technique test fixtures |
| **Could** | Domain-age lookup; redirect-chain inspection; ARC evaluation; transformer model; read-only IMAP/Gmail/Graph integration; browser extension; quarantine suggestions |
| **Won't (this release)** | Automatic mailbox-wide scanning without consent; mailbox write/quarantine actions; DMARC enforcement automation; full attachment detonation/sandboxing; retaining raw messages for training without explicit, separate consent |

---

## 4. Non-functional requirements

| Area | Requirement |
|---|---|
| Security | OWASP ASVS-aligned controls; parameterized queries; output encoding; CSRF tokens; secure headers; Argon2id/bcrypt password hashing; rate limiting; least privilege; audit log; dependency and secret scanning in CI |
| Privacy | Data minimization; purpose limitation; consent/authorization evidence; 90-day default retention; deletion; no raw email storage by default; no third-party analytics; no real `.eml` in the repository |
| Accessibility | WCAG 2.2 AA; axe-core in Playwright; manual keyboard, zoom and screen-reader spot checks; 44×44px targets; reduced motion |
| Performance | Dashboard p95 under 2s on a typical pilot dataset; analyzer p95 under 3s for a 5 MB `.eml`; API p95 under 500ms for standard queries (provisional targets) |
| Reliability | Idempotent event ingestion; retry-safe send jobs; no duplicate sends; scheduled jobs observable; graceful analyzer failures |
| Scalability | Pilot target: 2,000 targets, 20 concurrent users; pagination and background jobs for bulk operations |
| Observability | Structured logs with request IDs; metrics for sends, errors, queue depth and analyzer latency; audit log separate from application logs |
| Maintainability | Typed API contracts (OpenAPI), migrations via Alembic, tests for rules and permissions, versioned templates and models |
| Compatibility | Current evergreen browsers; responsive from 320px; PostgreSQL 16; Redis 7 |
| Localization | All UI strings in one content file; English first, Urdu planned as a could-have; no hard-coded copy |
| Legal/ethical | Authorization before launch; non-punitive reporting; group-level default; k≥5 suppression; retention; incident escalation |

---

## 5. Out of scope

- Real malware, weaponized attachments, credential harvesting or session-token theft.
- Filter-evasion, sender-spoofing evasion or infrastructure designed to bypass security controls.
- Real brand impersonation or use of real logos.
- Employee punishment, ranking or automated discipline.
- Sending to people outside the authorized organization.
- Full mailbox ingestion or write access to mailboxes in this release.
- Production SMTP relay without a signed pilot authorization and sandbox domain review.
- Mobile native apps.
- Payment or billing features.

---

## 6. Acceptance gates

Phase 2 can start only when:

- [ ] This requirements document is approved.
- [ ] Roles and permission matrix are accepted.
- [ ] Assumptions needing a decision are resolved or explicitly deferred.
- [ ] The phase 2 checklist is accepted.
