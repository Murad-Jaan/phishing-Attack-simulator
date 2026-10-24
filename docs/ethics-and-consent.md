# Ethics, Authorization and Consent

This document defines the non-negotiable ethical controls for the platform. It is operational guidance, not legal advice. The deploying organization must obtain its own legal and HR review before any pilot.

Source of truth for scope: [`PLAN.md`](PLAN.md). Defaults: [`assumptions.md`](assumptions.md).

---

## 1. Ethical position

The platform exists to **measure and improve resilience**, not to catch or punish people. It does this by:

- running only authorized, scoped simulations;
- collecting the minimum data needed for learning;
- explaining risk rather than issuing verdicts;
- reporting at group level by default;
- treating a click or report as information, never as misconduct;
- giving people immediate, blame-free feedback and an easy way to report;
- never capturing credentials, malware, real attachments or filter-evasion capability.

### 1.1 What the platform will never do

- Capture a password, one-time code, session token or any form field value.
- Send malware, weaponized documents, real attachments or exploit links.
- Impersonate a real brand, use real logos, or send from a domain the organization does not control.
- Evade mail filters, spoof authentication, or use infrastructure intended to bypass security controls.
- Target people outside the signed scope, or continue after authorization expires or is revoked.
- Rank, shame, discipline or automate consequences for individuals.
- Sell, share or repurpose simulation or analyzer data.
- Analyze a real mailbox without explicit, recorded consent and a lawful basis.

---

## 2. Authorization gate

No campaign may be scheduled or sent without an `approved` authorization that matches the campaign's current scope.

### 2.1 States

```
draft ──request──> pending ──approve──> approved ──launch──> active ──complete──> closed
  │                   │                    │
  │                   └──reject──> rejected │
  └──cancel──> cancelled                    └──expire/revoke──> expired/revoked
```

| State | Meaning | Can launch? |
|---|---|---|
| `draft` | Analyst is preparing the request | No |
| `pending` | Awaiting an admin who is not the creator | No |
| `approved` | Scope, dates and domains match; signed RoE reference recorded | Yes, until expiry |
| `active` | Campaign has started within the approved window | Yes, within scope |
| `rejected` | Approver declined with a reason | No |
| `expired` | Approval window passed | No |
| `revoked` | Approver or admin withdrew approval | No; stop unsent sends |
| `closed` | Campaign finished and reviewed | No |

### 2.2 Rules

1. **Separation of duties:** the approver must be an admin who is not the campaign creator. A second analyst cannot self-approve through a shared account.
2. **Scope binding:** approval covers named campaigns, groups, templates, sending domains, start/end dates, data collected and retention. Any change invalidates approval.
3. **Expiry:** approvals expire at the end date or after a maximum window (default 30 days; see assumptions). Expired approval blocks launch.
4. **Revocation:** an admin can revoke at any time. The system stops unsent messages, marks the campaign paused/cancelled and writes an audit entry.
5. **Evidence:** the approval stores the RoE version/hash, approver, timestamp, scope snapshot and any conditions. Uploaded authorization documents are stored encrypted and access-controlled, or only their hash/reference is stored if policy forbids upload.
6. **No retroactive approval:** a campaign already sent cannot be "approved after the fact".
7. **Emergency stop:** an admin can stop all running campaigns immediately. The audit log records who, when and why.

### 2.3 Launch checklist (enforced in UI and API)

- [ ] Signed authorization on file and referenced.
- [ ] Rules of engagement reviewed and versioned.
- [ ] Scope matches exactly (people, groups, dates, templates, domains).
- [ ] Sending domain is an approved sandbox domain.
- [ ] Test send completed and reviewed.
- [ ] Group size ≥ 5, or suppression acknowledged.
- [ ] Data collection limited to events in this document.
- [ ] Retention configured.
- [ ] Emergency contact and stop procedure confirmed.
- [ ] No real brand, logo, attachment or credential field present.
- [ ] Non-punitive reporting confirmed with HR/works council as required.

---

## 3. Rules of engagement (RoE) template

> Replace bracketed fields. Keep a signed copy outside the application if documents must not be uploaded.

### 3.1 Parties and authority

| Field | Value |
|---|---|
| Organization | `[Legal entity]` |
| Business unit / scope owner | `[Name, role]` |
| Platform owner | `[Name, role]` |
| Security lead | `[Name, role]` |
| HR / legal reviewer | `[Name, role]` |
| Works council / staff representative (if applicable) | `[Name / reference]` |
| Authorization reference | `[Document ID / hash]` |
| Effective dates | `[Start]` to `[End]` |
| Emergency contact and stop authority | `[Name, phone, backup]` |

### 3.2 Purpose and lawful basis

- Purpose: `[e.g. measure phishing resilience and improve awareness training]`
- Lawful basis / internal policy: `[e.g. legitimate interest, security policy, employee notice]`
- Explicitly **not** for: discipline, performance review, surveillance, or identifying "bad employees".

### 3.3 Scope

| Item | In scope | Out of scope |
|---|---|---|
| Target groups | `[Groups and approximate counts]` | `[Executives, contractors, unions, etc.]` |
| Sending domains | `[example.com / *.test / approved pilot domain]` | All real third-party brands |
| Templates / techniques | `[ATT&CK IDs and scenario IDs]` | Malware, real attachments, filter evasion |
| Dates and windows | `[Start/end, allowed hours, timezone]` | Outside approved window |
| Data collected | `[sent, opened, clicked, form_touched, answered, reported]` | Passwords, field values, full mailbox content |
| Retention | `[90 days default]` | Indefinite storage |
| Reports | Group-level; k≥5 suppression | Individual ranking or public dashboards |
| Integrations | `[Mailpit / approved relay / read-only mail API]` | Mailbox write, quarantine, forwarding rules |

### 3.4 Constraints and prohibitions

- No credential capture; simulated forms record only `form_touched`.
- No malware, real attachments, exploit links, or filter-evasion.
- No real brand names, logos or domains.
- No targeting outside the named groups.
- No use of results for discipline or performance management.
- No raw email retention without separate consent.
- No campaign launch without this signed RoE and a matching approval.

### 3.5 Data handling

- Data minimization per section 5.
- Access limited to named roles.
- Encryption in transit and at rest.
- Retention and deletion as configured.
- Incident and data-subject request process per section 7.
- No third-party analytics or advertising trackers.

### 3.6 Participant information and debrief

- Employees are informed through `[policy / intranet notice / onboarding]` that authorized simulations occur.
- After interaction, the awareness page is shown immediately and is blame-free.
- A debrief is available on request.
- Reporting is encouraged and never penalized.

### 3.7 Review and signature

| Role | Name | Signature | Date |
|---|---|---|---|
| Scope owner | | | |
| Security lead | | | |
| HR / legal | | | |
| Platform admin | | | |

**Conditions / exceptions:** `[List any]`

---

## 4. Consent and notice templates

### 4.1 Organizational authorization (short form)

> **Authorization for authorized phishing simulation**
>
> `[Organization]` authorizes `[Platform owner]` to conduct phishing simulations against `[groups]` between `[start]` and `[end]` for the purpose of security awareness. Simulations will use approved sandbox domains, will not capture passwords or form values, will not contain malware or real attachments, and will not use filter-evasion. Data is limited to delivery and interaction events, retained for `[90]` days, reported at group level, and never used for discipline. The signed rules of engagement `[reference]` form part of this authorization. Approval may be revoked at any time by `[role]`.
>
> Authorized by: `[Name, role, signature, date]`

### 4.2 Employee notice (intranet / policy)

> **Security awareness simulations**
>
> Our security team occasionally sends safe, simulated phishing messages to help us practise spotting scams. These are not real attacks. They never ask for or store your password, and they do not contain malware. Results are used to improve training and are reported by team, not to judge individuals. If you interact with a simulation, you will see a short explanation and tips. If you receive a suspicious message, use **Report phishing**. Reporting is always the right action, and you will never be penalized for reporting or for clicking.

### 4.3 Debrief / awareness copy (after a click)

> **This was a phishing simulation**
>
> No harm done, and no information was saved. Here are the signs that gave it away: `[red flags]`.
>
> 1. `[tip]`
> 2. `[tip]`
> 3. `[tip]`
>
> Reporting suspicious messages helps everyone. You can start a 3-minute training now, or close this page.

### 4.4 Real-mail analyzer consent

> **Analyze a real email**
>
> Only analyze messages you are authorized to handle. The analyzer checks headers, links, text and attachment names. By default it does not store the message; only the score, label, rule IDs and time are saved. Do not upload messages containing secrets unless your policy allows it. `[ ] I confirm I am authorized to analyze this message.`

### 4.5 Read-only mailbox connection consent (future)

> Connecting a mailbox grants **read-only** access to analyze headers, links and text. The platform does not send, delete, move or modify messages, and does not read attachments unless you select them. Access can be revoked at any time. Data retention: `[policy]`. Scope: `[mailbox / date range / folders]`.

---

## 5. Data-handling policy

### 5.1 Data minimization

| Data | Collected? | Purpose | Default retention |
|---|---|---|---|
| Target email, display name, department, external ID | Yes, if provided | Deliver and group | Until target deleted or retention |
| Campaign metadata | Yes | Operate and audit | Retention period |
| Event: sent, delivered, opened, clicked, form_touched, answered, reported | Yes | Measure and train | 90 days |
| Answer choice (`phish`/`legit`/`report`) | Yes | Learning feedback and aggregate metrics | 90 days |
| Simulated form field values | **Never** | — | — |
| Passwords / OTPs / tokens | **Never** | — | — |
| Raw `.eml` / pasted body | No by default | Analyze in memory | Not stored |
| Analyzer result: score, label, rule IDs, model version, timestamp | Yes, minimized | Explain and evaluate | 90 days (decision pending) |
| Full IP address | No by default | Abuse/rate limiting only if needed | Hashed/truncated, short-lived |
| User agent | Optional | Compatibility diagnostics | 30 days (decision pending) |
| Audit log | Yes | Accountability and investigation | 1 year (decision pending) |
| Authorization evidence | Yes | Legal/ethical compliance | Contract term + retention |
| Training progress | Yes | Employee learning | Until target deletion or retention |

### 5.2 Collection rules

- Collect only what a documented purpose requires.
- Do not use tracking pixels, fingerprinting, ad networks or third-party analytics.
- Passwords are never fields in the simulation; a form touch is recorded without reading input values.
- Event metadata is allow-listed; unknown fields are dropped, not stored.
- Analyzer input is processed in memory, bounded in size, and logged only as rule outcomes.
- Do not log request bodies for analyzer or authentication endpoints.
- Do not store raw email content in application logs, error trackers or audit entries.

### 5.3 Storage and access

- Encryption in transit (TLS) and at rest (database/volume encryption).
- Access by role; individual drill-down requires admin role and a logged reason.
- Least-privilege database accounts; no shared accounts.
- Backups follow the same retention and access rules.
- Secrets only in environment variables/secret manager; never in the repository.
- Real `.eml`, `.msg`, `.mbox` and `real-emails/` directories are git-ignored and must never be committed.

### 5.4 Retention and deletion

- Default retention: **90 days**, configurable (see assumptions).
- A scheduled job deletes or irreversibly anonymizes expired events, analyzer results, reports and training records.
- Audit entries follow a longer retention required for accountability; they contain no raw content.
- Admin delete-all requires typed confirmation, is audited, and covers the full selected scope.
- Backups expire on their own schedule; document the maximum backup age.
- Legal hold, if required, suspends deletion for a defined scope and is audited.

### 5.5 Data-subject requests

- Provide a documented contact and response process.
- Verify identity before disclosure or deletion.
- Distinguish platform data from mail-provider data.
- Record the request and outcome in the audit log without storing unnecessary personal data.

### 5.6 Breach and incident response

1. Contain: revoke sessions, pause campaigns, disable affected integration.
2. Assess: what data, whose, how long, legal/notification obligations.
3. Notify: follow organizational and legal requirements; do not hide incidents.
4. Remediate: rotate secrets, patch, fix access.
5. Review: blameless post-incident review, update this policy and tests.

---

## 6. Non-punitive reporting policy

### 6.1 Principles

- A click is a data point, not a disciplinary event.
- Reporting is always encouraged, including reporting a simulation.
- No individual scoreboards, rankings, public comparisons or "worst clicker" lists.
- No automated consequences, alerts to managers, or HR escalation based on simulation results.
- No use of results in performance reviews, promotion, pay or restructuring decisions.
- Reports describe groups and trends, not individuals.

### 6.2 Reporting rules

| Rule | Default |
|---|---|
| Default granularity | Group/department level |
| Minimum group size for reporting | 5 targets |
| Small-group handling | Suppress counts and rates; show "too small to report" |
| Individual detail | Admin only, with a logged reason and purpose |
| Individual export | Disabled by default |
| Manager view | Group aggregate only; no individual names |
| Employee view | Own learning progress only, never compared with others |
| Naming in reports | No individual names or emails in default reports |
| Tone | Blame-free; "No harm done"; explain signs and next steps |

### 6.3 Exceptions

Individual detail may be accessed only to:
- investigate a credible security incident,
- respond to a data-subject request,
- debug a platform defect with consent or under a documented process,
- meet a legal obligation.

Every access requires a reason, is limited in time, and is audited. Repeated or unjustified access is itself an incident.

### 6.4 Manager guidance

- Use results to plan team training, not to evaluate people.
- Do not ask "who clicked?".
- Praise reporting.
- Share aggregate lessons, not anecdotes that identify someone.
- Escalate only genuine security incidents (for example someone reports a real compromise), not simulation clicks.

---

## 7. Abuse reporting and escalation

| Situation | Action |
|---|---|
| Suspected misuse of the platform by an insider | Stop campaigns, preserve audit log, notify security lead and legal; do not confront alone |
| Unauthorized or out-of-scope campaign | Revoke authorization, stop sends, audit, notify scope owner |
| Credential capture attempted or discovered | Treat as a security incident; remove feature/path, rotate secrets, notify affected people |
| Real brand/domain misuse | Stop campaign, remove template, review approval process |
| Harassment or targeting of an individual | Stop immediately, preserve evidence, follow HR/legal process |
| Data leak or accidental raw-email storage | Contain, assess, notify per policy, delete, add regression test |
| Detector used to surveil a mailbox | Revoke access, audit, notify privacy/legal owner |
| Vulnerabilities in the platform | Follow coordinated disclosure; do not test against production without authorization |

**Emergency stop:** any admin can pause all campaigns. The system records actor, timestamp and reason; the security lead is notified.

---

## 8. Ethics review checklist (per campaign)

- [ ] Purpose is awareness, not punishment.
- [ ] Signed authorization matches scope.
- [ ] Approver is independent from creator.
- [ ] Target groups are named and in scope.
- [ ] Sending domain is an approved sandbox domain.
- [ ] Template contains no real brand, logo, attachment or credential field.
- [ ] Test send completed; rendering checked.
- [ ] Data collection is limited to allowed events.
- [ ] Retention configured.
- [ ] Group size ≥ 5 or suppression acknowledged.
- [ ] Non-punitive copy reviewed.
- [ ] Employee notice/debrief available.
- [ ] Emergency stop and contact confirmed.
- [ ] Report-phish path works.
- [ ] Results will be reviewed at group level.

---

## 9. Open ethics decisions

Tracked in [`assumptions.md`](assumptions.md):

- Whether employees are notified before each campaign or only through standing policy.
- Whether works council/staff representative approval is mandatory in the deploying jurisdiction.
- Whether authorization documents may be uploaded or only referenced by hash.
- Whether analyzer metadata retention is 90 days or shorter.
- Whether individual detail should ever be visible to analysts (currently admin-only).
- Maximum authorization window and default campaign window.
