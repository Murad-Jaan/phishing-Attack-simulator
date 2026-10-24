# Threat Model

Scope: the rebuilt platform (frontend, API, workers, database, mail delivery, analyzer) and its authorized use. Sources: [`PLAN.md`](PLAN.md), [`requirements.md`](requirements.md), [`ethics-and-consent.md`](ethics-and-consent.md).

**Method:** asset-driven analysis with abuse cases, STRIDE prompts, MITRE ATT&CK coverage and a kill-chain view. This is a living document; update it at every phase and after any incident.

---

## 1. Assets

| ID | Asset | Why it matters | Impact if compromised |
|---|---|---|---|
| AS-01 | Target personal data (email, name, department, external ID) | Privacy and trust | Harassment, privacy breach, regulatory exposure |
| AS-02 | Campaign scope and schedules | Safety and consent | Unauthorized sends, reputational harm |
| AS-03 | Authorization evidence and RoE | Legal/ethical defensibility | Unable to prove consent; misuse |
| AS-04 | Templates and red-flag content | Training integrity | Brand/legal issues, harmful lures |
| AS-05 | Event data (sent, opened, clicked, form touched, answered, reported) | Measurement and learning | Shaming, surveillance, re-identification |
| AS-06 | Individual drill-down and exports | Privacy | Targeted retaliation or discrimination |
| AS-07 | Audit log | Accountability | Covering tracks, failed investigations |
| AS-08 | User credentials, sessions and CSRF tokens | Account security | Account takeover, unauthorized campaigns |
| AS-09 | Mail infrastructure and sending domains | Deliverability and reputation | Spam relay, blocklisting, domain abuse |
| AS-10 | Analyzer inputs (headers, links, text, attachment names) | Sensitive real email | Data leak, mailbox surveillance |
| AS-11 | Detection rules, features and model artefacts | Defensive capability | Evasion, poisoning, false confidence |
| AS-12 | Application secrets, database and backups | Platform integrity | Full compromise |
| AS-13 | Report-phish submissions | Incident response | Missed real compromise, reporter exposure |
| AS-14 | Availability and queue capacity | Operations | Denial of service, missed training window |

---

## 2. Actors and trust boundaries

### 2.1 Actors

| Actor | Intent | Capability |
|---|---|---|
| **Employee (target)** | Learn; may be curious or anxious | Receives simulations; can report; may click or submit the simulated form |
| **Analyst** | Create and run campaigns, triage, analyze | Template/group/campaign access; cannot approve or view individual detail |
| **Admin** | Operate safely and comply | Broad access; can approve, revoke, export, delete, audit |
| **Malicious or careless insider** | Harass, surveil, self-approve, leak | Legitimate account with elevated intent or error |
| **External attacker** | Take over accounts, exfiltrate data, abuse relay | Internet access; credential attacks; web exploitation |
| **Unauthorized organization member** | Run a campaign without consent | May obtain an account or trick an approver |
| **Mail/cloud provider** | Deliver or store mail | Sees message metadata/content per contract |
| **Dependency/CI attacker** | Supply-chain compromise | Build or dependency access |
| **Auditor / legal reviewer** | Verify compliance | Read-only evidence access |

### 2.2 Trust boundaries

| Boundary | Untrusted side | Controls |
|---|---|---|
| Browser ↔ Next.js/FastAPI | All user input, uploaded `.eml`, pasted headers | Output encoding, CSP, CSRF, session cookies, validation, size limits, rate limits |
| API ↔ PostgreSQL | Application queries | Parameterized queries, least-privilege DB role, migrations, encryption |
| API/worker ↔ mail relay | External delivery | Sandbox domain allowlist, authorization check, rate limit, no open relay, TLS |
| Analyzer ↔ DNS/blocklist | External lookups | No URL fetching; bounded DNS; allowlisted resolvers; timeouts; no attachment execution |
| Admin ↔ platform | Privileged actions | Strong auth, separation of duties, reason-logged drill-down, audit |
| Organization ↔ platform | Data subjects and scope | Written authorization, target allowlist, group suppression, retention |
| CI ↔ repository | Build and dependencies | Pinned actions, least-privilege tokens, secret scanning, CodeQL, review |
| Platform ↔ third parties | Vendors | Data-processing terms, no analytics/ad tracking, minimal sharing |

---

## 3. Abuse cases and mitigations

| ID | Abuse case | STRIDE | Likelihood | Impact | Mitigations |
|---|---|---|---|---|---|
| AB-01 | Insider runs a campaign without authorization or outside scope | Elevation / Repudiation | Medium | High | Authorization gate; separation of duties; scope binding; target allowlist; audit; emergency stop; alert on out-of-scope targets |
| AB-02 | Harassment: target one person or a small group with humiliating content | Tampering / Info disclosure | Medium | High | Minimum group size; individual detail restricted; template review; no free-form targeting; group suppression; audit |
| AB-03 | Capture real passwords or OTPs | Info disclosure | Low (if built correctly) | Critical | No credential fields; form touch event only; code review and automated tests; CSP; output encoding |
| AB-04 | Impersonate a real brand or use real logos | Spoofing | Medium | High | Sandbox domain allowlist; template review; asset checks; no real brands in seed data; approval checklist |
| AB-05 | Deliver malware or a real attachment | Tampering | Low | Critical | No attachment upload/execution in simulations; display-name-only attachments; content review; no MIME payloads |
| AB-06 | Filter evasion or auth spoofing | Spoofing | Low | Critical | No evasion features; sandbox domains only; SPF/DKIM/DMARC on sending domains; abuse monitoring |
| AB-07 | Use the platform as a spam relay | Abuse | Low | High | Authorization required; approved domains; per-campaign caps; rate limits; relay credentials scoped; queue monitoring |
| AB-08 | Mailbox surveillance through analyzer or IMAP | Info disclosure | Medium | High | Explicit consent; read-only scope; no raw retention; content minimization; access logs; no mailbox write |
| AB-09 | Raw email leaks via logs, uploads, errors or exports | Info disclosure | Medium | High | No request-body logging; in-memory analysis; redaction; export allowlist; retention; git-ignore `.eml`; CI secret scan |
| AB-10 | Forge authorization or self-approve | Elevation / Repudiation | Medium | High | Independent approver; immutable audit; approval reference hash; scope snapshot; admin-only approval; no backdating |
| AB-11 | IDOR / privilege escalation to other orgs or groups | Elevation | Medium | High | Every query scoped by `org_id`; object-level authorization tests; role checks server-side; deny by default |
| AB-12 | Mass export of target or event data | Info disclosure | Medium | High | Export RBAC; group-level only for analysts; reason and audit; rate limits; no individual rows without permission |
| AB-13 | Detector poisoning or feedback manipulation | Tampering | Medium | Medium | Feedback is advisory; model retraining gated; provenance and review; evaluate on held-out sets; anomaly monitoring |
| AB-14 | Resource exhaustion via huge `.eml` or pasted content | DoS | Medium | Medium | 5 MB upload / 2 MB paste caps; timeouts; queue isolation; rate limits; parser sandbox; memory limits |
| AB-15 | Phish the admins through templates or support flows | Spoofing | Medium | High | Templates are clearly internal; no real external send; admin UI labels; review; no credential prompts |
| AB-16 | Re-identify individuals from small groups or "needs training" lists | Info disclosure | Medium | High | k≥5 suppression; no individual lists default; aggregate only; individual detail reason-logged |
| AB-17 | Use results for discipline or performance review | Repudiation / abuse | Medium | High | Policy + UI language; no individual exports default; manager guidance; audit individual access |
| AB-18 | Supply-chain compromise via dependency or action | Tampering | Medium | High | Lockfiles; pinned actions; Dependabot; CodeQL; secret scanning; SBOM; review before upgrade |
| AB-19 | Stored XSS via template/email content or analyzer output | Tampering | Medium | High | Framework escaping; sanitize email HTML with allowlist; CSP; test payload fixtures |
| AB-20 | CSRF, clickjacking or session theft | Spoofing / Elevation | Medium | High | SameSite cookies; CSRF tokens; Origin checks; frame-ancestors; HttpOnly; session rotation; idle timeout |
| AB-21 | Spreadsheet formula injection in CSV exports | Tampering | Medium | Medium | Prefix `= + - @` with `'`; quote and escape; tests |
| AB-22 | SSRF or DNS abuse through URL analysis | Info disclosure / DoS | Medium | Medium | Never fetch URLs server-side; parse only; DNS via allowlisted resolver with timeouts; no internal ranges |
| AB-23 | Unauthorized access to audit log or tampering | Repudiation | Low | High | Admin-only, append-only for app users, redacted, separate retention, export audited |
| AB-24 | Accidentally sending outside the approved window | Repudiation | Medium | Medium | Server-side schedule checks; authorization expiry; timezone display; confirmation |
| AB-25 | Target data imported without lawful basis | Info disclosure | Medium | High | Import consent/authorization reference; data minimization; deletion; retention; audit |

---

## 4. MITRE ATT&CK coverage

### 4.1 Technique coverage

| ATT&CK ID | Technique | Scenario(s) | Simulation vector | Detection signals in the platform |
|---|---|---|---|---|
| **T1566.001** | Phishing: Spearphishing Attachment | **SC-03** (invoice with `.pdf.exe`) | Attachment name or simulated attachment; never a real executable | Double extension, risky type, unexpected invoice, payment pressure, sender reputation |
| **T1566.002** | Phishing: Spearphishing Link | **SC-01** (PayPal lookalike), **SC-06** (document share), **SC-08** (delivery fee) | Tokenized link to awareness/simulated page | Display-vs-href mismatch, lookalike domain, digit substitution, urgency, credential/payment request |
| **T1566.003** | Phishing: Spearphishing via Service | **SC-09** (proposed; simulated sandbox chat/file-sharing service) | Delivery through a simulated third-party chat/file-sharing channel, not ordinary email | Third-party service channel, unexpected share, re-authentication, sender/service mismatch |
| **T1566** | Phishing (generic parent) | **SC-05** (BEC-style CEO impersonation) | Reply-only social-engineering lure; no link or attachment | Free-mail executive, gift-card request, secrecy, out-of-band verification prompt |
| **T1598** | Phishing for Information | **SC-10** (proposed; fake IT service desk identity check) | Reply/phone follow-up, no attachment or link required | Identity-data request, authority, urgency, no ticket reference |
| **T1656** | Impersonation (secondary mapping) | **SC-05** | Impersonates a CEO from a free-mail account to request gift cards | Display-name/address mismatch, authority, secrecy |

**Coverage status:** all four required techniques (T1566.001, T1566.002, T1566.003, T1598) have at least one scenario. T1566.003 relies on proposed **SC-09**, which must be delivered through the simulated service channel itself. T1598 relies on proposed **SC-10**. **SC-05** is a BEC-style CEO-impersonation case mapped to generic **T1566**, with **T1656 Impersonation** as a secondary mapping; it is not used for T1598 coverage. Legacy `index.html` is not edited; proposals belong in the new seed data and tests.

### 4.2 Scenario-to-technique detail

| Scenario | Technique | Tactic | Why it maps | Simulated red flags |
|---|---|---|---|---|
| SC-01 | T1566.002 | Initial Access | Link to a credential-looking page | Lookalike domain, urgency, generic greeting |
| SC-02 | — (benign control) | — | Legitimate internal message | None; tests false-positive restraint |
| SC-03 | T1566.001 | Initial Access | Attachment lure | Double extension, unknown vendor, payment pressure |
| SC-04 | — (benign control) | — | Legitimate maintenance notice | None; tests restraint |
| SC-05 | T1566 (generic); T1656 (secondary) | Initial Access (T1566); T1656 tactic to verify against current MITRE ATT&CK (believed Defense Evasion) | Elicits gift-card codes and secrecy; BEC-style CEO impersonation | Free-mail executive, unusual request, secrecy, avoids phone |
| SC-06 | T1566.002 | Initial Access | Link to a lookalike document portal | Lookalike domain, curiosity, re-authentication |
| SC-07 | — (benign control) | — | Legitimate password-expiry notice | None; teaches safe verification |
| SC-08 | T1566.002 | Initial Access | Link to payment page | Unofficial domain, unexpected parcel, payment |
| SC-09 | T1566.003 | Initial Access | Notification delivered through a simulated third-party chat/file-sharing service channel | Service channel, unexpected share, re-authentication, channel mismatch |
| SC-10 | T1598 | Reconnaissance | Requests identity details to "verify" | Authority, urgency, request for personal data, no ticket reference |

### 4.3 Kill-chain view (attacker and defender)

| Stage | Attacker/simulation action | Platform control | Detection/response opportunity |
|---|---|---|---|
| **Recon** | Select targets, departments, reporting lines | Target groups are explicit and authorized; no reconnaissance module; minimal data | Access review; group membership audit; k≥5 suppression |
| **Lure design** | Choose technique, pretext, sender, subject | Template library restricted to ATT&CK IDs and approved sandbox domains; review checklist | Template review; red-flag metadata; content lint for brands/credentials |
| **Delivery** | Send via Mailpit or approved relay | Authorization gate; scope/date/domain binding; per-campaign caps; TLS; no open relay | Queue monitoring; send audit; bounce/abuse alerts; revocation stops sends |
| **User action** | Open, click, touch form, reply | Tokenized links; no credential fields; `form_touched` on focus/first input only, never values/keystrokes, field labelled as simulation; no real attachments | Event ingestion; teachable moment; anomaly (unexpected click spike) |
| **Awareness** | (Defender) immediate feedback | Blame-free page under 3 minutes; red flags; training | Completion tracking; group-level trends; support path |
| **Report** | (Defender) user reports phish | One-click report; IT triage; feedback into detector | Time-to-report; triage status; detector rule tuning; no punishment |

### 4.4 Defensive technique mapping (optional)

| Defensive idea | ATT&CK mitigation / control |
|---|---|
| Email authentication on sending domains | M1054? / SPF, DKIM, DMARC operational practice |
| MFA, preferably phishing-resistant | M1032 |
| User training | M1017 |
| Restrict web-based content / link inspection | M1021 |
| Audit | M1047 (audit) |
| Least privilege | M1026 |
| Network segmentation for analyzer | M1030 |

Use these as design prompts, not certification claims.

---

## 5. Security requirements traceability

| Requirement | Threat/abuse addressed | Where enforced |
|---|---|---|
| Authorization gate and scope binding | AB-01, AB-10, AB-24 | API service layer, DB constraints, audit |
| Separation of duties | AB-01, AB-10 | Role checks; approver ≠ creator |
| No credential fields; `form_touched` on focus/first input, never values/keystrokes, labelled as simulation | AB-03 | Frontend component and event schema |
| Sandbox domain allowlist | AB-02, AB-04, AB-06, AB-07 | Organization settings + send service |
| No attachments executed | AB-05 | Template schema and analyzer (parse only) |
| No URL fetching | AB-22 | Analyzer design |
| Group suppression k≥5 | AB-16 | Reporting queries and UI |
| Individual detail reason + audit | AB-16, AB-17 | Admin endpoint + audit |
| Export RBAC and CSV hardening | AB-12, AB-21 | Export service |
| Parameterized queries and org scoping | AB-11 | SQLAlchemy repositories |
| CSRF, SameSite, HttpOnly, rate limits | AB-20 | API middleware |
| Output encoding and HTML sanitization | AB-19 | React escaping, sanitizer |
| No raw content logging/retention | AB-08, AB-09 | Logging config, analyzer service |
| Upload size limits, timeouts | AB-14 | API limits, worker config |
| Audit append-only and redacted | AB-10, AB-23 | Audit service + DB permissions |
| Pinned actions, lockfiles, scans | AB-18 | CI |
| Emergency stop | AB-01, AB-24 | Admin endpoint + worker cancellation |

---

## 6. Residual risks

| Risk | Why it remains | Owner action |
|---|---|---|
| Determined admin can still misuse legitimate access | Separation of duties and audit deter but do not prevent collusion | Monitor audit; require two-person approval for sensitive changes; periodic access review |
| Small groups can still be inferred despite suppression | Context may reveal membership | Raise k if needed; avoid reporting tiny units; document |
| Rules and models produce false positives/negatives | Detection is probabilistic | Show reasons; allow feedback; evaluate on held-out data; never auto-punish |
| Employees may feel surveilled | Simulation is inherently observability | Clear notice, non-punitive policy, group-only reporting, transparency |
| Mail provider or relay sees content | Delivery requires a provider | Choose provider with terms; sandbox content; minimize data; no real secrets |
| Insider leaks exported aggregates | Exports are legitimately needed | Audit exports; watermark/limit; policy; data-loss monitoring |
| Analyzer may parse malicious MIME | Even parsing untrusted input carries risk | Sandboxed parser, size/time limits, no execution, dependency patching |
| Dependencies and CI supply chain | External code is trusted by default | Pinning, SBOM, scans, reviews, least-privilege tokens |
| No MFA in the first pilot | Usability and scope | Require MFA for admins; plan passkeys/FIDO2; document exception |
| Legal/works-council requirements vary | Not a legal tool | Local review before pilot; configurable notice/approval |

---

## 7. Review triggers

Re-run this threat model when:
- a new role, integration, mail provider or data field is added;
- analyzer gains mailbox access or URL fetching;
- individual-level reporting or exports change;
- a new scenario/technique is introduced;
- an incident, near-miss or penetration-test finding occurs;
- retention, authorization or approval rules change.

**Phase 1 sign-off:** coverage confirmed for T1566.001, T1566.002, T1566.003 and T1598. SC-05 maps to T1566 with T1656 secondary. SC-09/SC-10 are proposed and must be delivered via the simulated service channel where applicable; no legacy edits.
