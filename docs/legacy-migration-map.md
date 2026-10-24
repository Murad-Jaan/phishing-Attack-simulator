# Legacy Inventory and Migration Map

Phase 1 reference for the v1 app preserved in [`../legacy/index.html`](../legacy/index.html), [`../legacy/scripts/test.js`](../legacy/scripts/test.js) and [`../legacy/scripts/security-check.sh`](../legacy/scripts/security-check.sh).

**Principle:** the legacy app is a behavioural and detection reference. Port logic deliberately, with tests. Do not copy the single-file architecture, client-side state or simulated randomness.

| Item | Value |
|---|---|
| Source | `legacy/index.html` (227 lines), `legacy/scripts/test.js` (60 lines), `legacy/scripts/security-check.sh` (27 lines) |
| Scenarios | 8 (SC-01…SC-08) |
| Detection rules | 15 content/sender rules + 8 email/header rules + score bands |
| Tests | 10 Node tests |
| Security checks | 7 pass/fail checks plus 1 informational `innerHTML` count (not pass/fail) |
| Persistence | Browser `localStorage` key `psim` only |
| Network | None; CSP `default-src 'none'` |

---

## 1. Features

| ID | Feature | Legacy location | Behaviour |
|---|---|---|---|
| F-01 | IT dashboard KPIs | `it()` | Campaign count, simulated emails sent, links clicked, reports, correct/incorrect |
| F-02 | Campaign creator | `newCamp()` | Name, department filter (`All` + 4), difficulty filter (`mixed`/easy/medium/hard); snapshots employee and scenario indexes |
| F-03 | Auto-simulate responses | `simulate()` | Generates random answers and clicks for the latest campaign using a skill probability |
| F-04 | CSV export | `exportCsv()` | Campaign, employee, department, subject, is-phishing, link-clicked, answer, correct; neutralizes spreadsheet formula injection |
| F-05 | Reset demo data | `reset()` | Confirm dialog, clears campaigns and results |
| F-06 | Response accuracy chart | `it()` | Donut of correct vs incorrect responses |
| F-07 | Department awareness | `it()` | Average score per department with colour thresholds |
| F-08 | Employee awareness scores | `it()` | Individual score table with bars |
| F-09 | Needs extra training | `it()` | Lists individuals below 60 |
| F-10 | Campaign history | `it()` | Reverse-ordered table of campaigns |
| F-11 | Detection/prevention panel | `dpPanel()` | Detection, click and report rates, false alarms, generated recommendations |
| F-12 | Employee selector | `emp()` | Switches the demo employee |
| F-13 | Inbox | `emp()` | Lists campaign scenarios targeted at the selected employee |
| F-14 | Email detail | `emp()` | Sender, subject, body, link and attachment display |
| F-15 | On-demand detector scan | `emp()` + `scan()` | Runs rules on the selected email and shows reasons |
| F-16 | Simulated link/attachment click | `clickLink()` | Sets `click`, opens the fake-login state |
| F-17 | Fake login page | `emp()` | Disabled email/password inputs; states nothing is collected |
| F-18 | Answer actions | `answer()` | Phishing / Legitimate / Report suspicious |
| F-19 | Instant feedback | `emp()` | Correctness, actual label, red-flag list, prevention tip |
| F-20 | Employee score | `score()` | Accuracy minus 10 per phishing click; `null` with no answers |
| F-21 | Email risk analyzer | `dp()` + `analyze()` | Sender, link and text inputs; rule score and reasons |
| F-22 | Load analyzer sample | `sample()` | Fills the known PayPal-style sample |
| F-23 | Gmail paste flow | `dp()` | Pastes `Show original` text and scans locally |
| F-24 | `.eml` upload | `eml()` + `emlText()` | Max 5 MB, parsed locally, never uploaded |
| F-25 | Header analysis | `emlText()` | SPF/DKIM/DMARC, Reply-To and Return-Path mismatches |
| F-26 | Link destination analysis | `emlText()` | Anchor text vs real href, shorteners, IPs, `@`, mismatched domains |
| F-27 | Attachment analysis | `emlText()` | Risky extensions and double extensions |
| F-28 | "What to do" advice | `emlText()` | Risk-specific response steps |
| F-29 | Prevention layers | `dp()` | Technical, people/process and response guidance |
| F-30 | Safe-habits checklist | `dp()` | Six self-report habits with progress bar |
| F-31 | Attack visualization | `attack()` | Five-step animated attack flow with defences; respects reduced motion |
| F-32 | Tips page | `tips()` | Reuses attack visualization and seven tips |
| F-33 | Theme support | CSS | Light/dark via system preference and `data-theme` |
| F-34 | Responsive layout | CSS | Auto-fit grids, horizontal scroll for wide tables |
| F-35 | XSS escaping | `esc()` | Escapes `& < > " '` before `innerHTML` |
| F-36 | Local-only privacy | CSP | No network calls, external scripts or styles |

---

## 2. Data fields

### 2.1 Employees (`EMP`, line 49)

Eight tuples: `[name, department]`.

| Index | Name | Department |
|---|---|---|
| 0 | Ali | IT |
| 1 | Zain | IT |
| 2 | Sara | HR |
| 3 | Maria | HR |
| 4 | Bilal | Finance |
| 5 | Hina | Finance |
| 6 | Usman | Sales |
| 7 | Ayesha | Sales |

Departments (`DEPTS`, line 50): IT, HR, Finance, Sales.

### 2.2 Scenario (`SC`, lines 51–59)

| Field | Meaning |
|---|---|
| `d` | Difficulty: easy, medium, hard |
| `p` | Is phishing: `1` = phishing, `0` = legitimate control |
| `from` | Sender address |
| `sub` | Subject |
| `body` | Plain-text body |
| `link` | Optional URL |
| `att` | Optional attachment filename |
| `ind` | Red-flag explanations shown after answering |

### 2.3 Runtime state (`S`, line 60)

| Field | Meaning |
|---|---|
| `camps[]` | Campaigns: `id`, `name`, `dept`, `diff`, `emps[]`, `scs[]`, `date` |
| `res{}` | Results keyed `campaignId|scenarioIndex|employeeIndex`; value `{click?: boolean, a?: "phish"|"legit"|"report"}` |
| `view` | Current screen: `it`, `emp`, `dp`, `tips` |
| `me` | Selected employee index |
| `openK` | Opened email key |
| `fake` | Fake-login visible flag |
| `lastDone` | Legacy UI flag |
| `scanOn{}` | Per-email detector visibility |
| `DC[]` | Safe-habits checklist state |
| `ORG` | Organization domain, default `company.com` |
| `lastP` | Last content score |

Persistence: `localStorage["psim"]` stores `S`; all other state is in-memory.

### 2.4 UI/CSS fields

Design tokens: `--bg`, `--card`, `--tx`, `--mu`, `--bd`, `--pr`, `--ok`, `--bad`, `--warn`; light/dark values; safe-area insets. Animations: `fi`, `lit`; reduced-motion override.

---

## 3. Scenario inventory

| ID | Difficulty | Phishing | Sender | Subject | Attack vector | ATT&CK | Legacy flags |
|---|---|---|---|---|---|---|---|
| SC-01 | easy | Yes | `security@paypa1-support.com` | URGENT: Your account will be suspended! | Link | T1566.002 | Misspelled domain (`1`), urgency/threat, generic greeting |
| SC-02 | easy | No | `hr@company.com` | Team lunch this Friday | Benign control | — | Known internal domain, no link/pressure |
| SC-03 | medium | Yes | `accounts@vendor-billing.co` | Invoice #8841 attached | Attachment | T1566.001 | Double extension `.pdf.exe`, unknown vendor, payment pressure |
| SC-04 | medium | No | `it@company.com` | Scheduled maintenance on Sunday | Benign control | — | Internal sender, no action requested |
| SC-05 | medium | Yes | `ceo.office@gmail.com` | Quick favor — keep confidential | Reply/social engineering (no link); BEC-style CEO impersonation | T1566 (generic); T1656 secondary | Free-mail CEO, gift-card request, secrecy, avoids phone |
| SC-06 | hard | Yes | `noreply@company-docs.net` | Shared with you: Q3 Salary Review | Link | T1566.002 | Lookalike domain, curiosity, re-authentication |
| SC-07 | hard | No | `it@company.com` | Password expires in 7 days | Benign control | — | Exact internal domain, real SSO, gentle deadline |
| SC-08 | hard | Yes | `delivery@dhl-tracking-pk.com` | Package delivery failed — reschedule | Link | T1566.002 | Unofficial DHL domain, unexpected parcel, payment link |

### 3.1 Proposed scenarios (not in legacy; do not edit legacy)

| ID | Difficulty | Phishing | Proposed scenario | Attack vector | ATT&CK | Gap filled |
|---|---|---|---|---|---|---|
| SC-09 | medium | Yes | A simulated sandbox chat/file-sharing service sends "A document was shared with you"; the link opens a simulated consent screen inside the service channel | Service-based delivery via a simulated third-party chat/file-sharing channel | T1566.003 | No legacy scenario uses a service-based delivery vector |
| SC-10 | medium | Yes | Fake IT service desk asks the target to confirm identity details (employee ID, phone) to "close a ticket" | Reply/phone follow-up, no attachment | T1598 | Makes phishing-for-information coverage explicit and testable |

SC-05 is a BEC-style CEO-impersonation case. It maps to generic **T1566** (not T1598); the impersonation also aligns with **T1656 Impersonation**. SC-10 is the primary T1598 scenario, so T1598 coverage does not depend on SC-05. SC-09's delivery must occur through the simulated service channel itself, not ordinary email, for T1566.003 to be accurate.

---

## 4. Detection inventory

### 4.1 Content and sender rules (`scan()`, lines 157–179)

| ID | Rule | Weight | Match |
|---|---|---|---|
| S-01 | Sender outside organization domain | +15 | Domain present and not equal to `ORG` |
| S-02 | Free webmail for official request | +15 | `gmail`, `yahoo`, `hotmail`, `outlook` `.com` |
| S-03 | Digit inside domain name | +25 | Digit before the final suffix |
| S-04 | Bait words in domain | +10 | `verify`, `support`, `secure`, `billing`, `tracking`, `docs`, `login` |
| S-05 | Unencrypted link | +15 | URL starts `http://` |
| S-06 | Raw IP link | +25 | `//` followed by dotted-quad IP |
| S-07 | Shortened link | +15 | `bit.ly`, `tinyurl`, `t.co`, `goo.gl` |
| S-08 | `@` in URL | +20 | Can hide the real host |
| S-09 | Link/sender domain mismatch | +10 | Neither host ends with the other |
| S-10 | Urgent/threatening language | +20 | `urgent`, `immediately`, `within 24`, `suspend`, `expires today/now/tonight`, `final notice`, `act now`, `permanently` |
| S-11 | Credential/personal-data request | +20 | `password`, `verify your account`, `sign in`, `log in`, `login`, `otp`, `ssn`, `pin` |
| S-12 | Money/payment request | +15 | `gift card`, `wire transfer`, `payment`, `invoice`, `fee` |
| S-13 | Generic greeting | +10 | `dear customer/user/sir/member` |
| S-14 | Risky attachment extension | +25 | `.exe`, `.js`, `.scr`, `.bat`, `.zip` mentioned in text |
| S-15 | Secrecy pressure | +10 | `confidential`, `don't tell`, `keep this private`, `secret` |

Score is capped at 100.

**Bands:** `<30` Low risk (green), `30–59` Medium risk (warning), `60–100` High risk: likely phishing (danger).

### 4.2 Email/header rules (`emlText()`, lines 181–208)

| ID | Rule | Weight | Notes |
|---|---|---|---|
| E-01 | No SPF/DKIM/DMARC results | +10 | No `Authentication-Results` and no `Received-SPF` |
| E-02 | SPF fail/softfail/none | +20 | Header check |
| E-03 | DKIM fail/none | +20 | Header check |
| E-04 | DMARC fail/none | +25 | Header check |
| E-05 | Reply-To domain differs from From | +20 | Header check |
| E-06 | Return-Path domain differs from From | +10 | Header check |
| E-07 | Anchor text domain differs from href host | +25 | Deceptive link text |
| E-08 | Risky attachment filename | +25 | `exe`, `js`, `scr`, `bat`, `vbs`, `iso`, `docm`, `xlsm`, `zip` |
| E-09 | Content scan integration | S-01…S-15 | Uses first link plus subject, body and attachment names |
| E-10 | Quoted-printable decoding | — | Applied when message declares quoted-printable |
| E-11 | Header folding and address extraction | — | Joins folded lines; extracts first address |
| E-12 | Total score and action advice | — | Header + content capped at 100; risk-specific next steps |

**Parser limits:** upload 5 MB, raw text sliced to 2 MB, analyzed body text sliced to 4,000 characters. Link list deduplicated; first 10 shown. The parser does not handle every MIME variant.

### 4.3 Explainability

Every rule appends a plain-language reason. The UI shows:
- a label and 0–100 score,
- header-check reasons,
- content-check reasons,
- link destinations (host plus anchor text),
- a "What to do" action list.

This is the direct ancestor of the new "Why was this flagged?" requirement.

---

## 5. Scoring and metrics

| Function | Behaviour |
|---|---|
| `ok(scenario, answer)` | Phishing scenarios are correct for `phish` or `report`; legitimate scenarios are correct only for `legit` |
| `score(employee)` | Percentage of correct answers minus 10 per phishing link click; `null` with no answers; floored at 0 |
| `stats()` | Sent = campaigns × targets × scenarios; clicks; reports; correct; incorrect |
| `dpPanel()` | Detection rate = phishing answers excluding `legit`; click rate; report rate; false alarms = safe scenarios marked non-legit; threshold-based recommendations |
| `colr()` | Score colour: ≥70 green, ≥40 warning, otherwise danger |
| CSV quoting | Wraps values in quotes, doubles quotes, prefixes `= + - @` with `'` |

Recommended actions in legacy:
- detection <70% → extra training for weakest departments,
- click rate >20% → MFA plus gateway blocking,
- report rate <30% → promote reporting and reward reporters,
- any false alarms → teach sender-domain verification,
- otherwise → continue monthly at higher difficulty.

---

## 6. Tests (`legacy/scripts/test.js`)

| ID | Test | What it proves |
|---|---|---|
| T-01 | Every scenario separates phishing from legitimate | Lowest phishing ≥30; highest legitimate <30 |
| T-02 | Sample phishing email is high risk | `scan()` score ≥60 |
| T-03 | `ok()` answer logic | Correctness for phish/report/legit |
| T-04 | `score()` accuracy and click penalty | 100% clean, 90% with one click, `null` with no data |
| T-05 | `esc()` neutralizes HTML and quotes | No raw `< > " '` |
| T-06 | Campaign creation, auto-simulation, stats | Department/scenario filters and sent count |
| T-07 | All views render | Each view produces content |
| T-08 | Forged headers and deceptive link | High risk, SPF/DMARC/Reply-To/anchor mismatch reasons |
| T-09 | Clean message is low risk | Passed authentication and internal sender |
| T-10 | CSV formula injection neutralized | Leading `=` is prefixed with `'` |

---

## 7. Security checks (`legacy/scripts/security-check.sh`)

| ID | Check |
|---|---|
| C-01 | No `eval()` or `new Function()` |
| C-02 | No `document.write()` |
| C-03 | No `fetch`, XHR, WebSocket or `sendBeacon` |
| C-04 | No external scripts or stylesheets |
| C-05 | No hard-coded secrets or private keys |
| C-06 | No enabled password field |
| C-07 | CSP `default-src 'none'` present |
| C-08 | **Informational only (not pass/fail):** reports the `innerHTML` count; user/email content still requires escaping |

C-01…C-07 are pass/fail. C-08 is only an informational count. The new stack replaces these single-file checks with framework security, server-side authorization, CI secret scanning, SAST, dependency scanning and Playwright security regression tests.

---

## 8. Migration map

| Legacy item | New owner | Decision | Notes |
|---|---|---|---|
| F-01 dashboard KPIs | `frontend/` + `backend/` reporting | Port | Add group-level suppression and table alternatives |
| F-02 campaign creator | Phase 2 campaigns + authorization | Port and extend | Add stepper, draft, test send, authorization gate |
| F-03 auto-simulate | dev-only seed tooling | Remove from production; replace with a dev-only demo seed script that creates clearly labeled demo events; never run in production; metrics in production come from real events only | No random or fabricated human responses in production; seeded demo data must be visibly marked and excluded from real reporting |
| F-04 CSV export | Phase 3 exports | Port | Keep formula-injection protection; enforce RBAC/audit |
| F-05 reset | Phase 2 settings | Replace | Retention job plus delete-all with confirmation and audit |
| F-06/F-07/F-08/F-09 charts | Phase 3 reports | Port | Group-level default; no individual shaming; accessible alternatives |
| F-10 campaign history | Phase 2/3 campaigns | Port | Server-side pagination and filters |
| F-11 recommendations | Phase 3/4 | Port and extend | Explain reasons; tie to detector and training |
| F-12/F-13/F-14 inbox | Phase 3 awareness | Replace | Real campaign delivery and event tracking |
| F-15 on-demand scan | Phase 4 analyzer | Port | Same rules with versioned reasons |
| F-16 click | Phase 3 tracking | Port | Record `clicked`; tokenized per-target links |
| F-17 fake login | Phase 3 tracking | Port narrowly | Record `form_touched` on focus or first input only; never read the field value, never log keystrokes; label the field as a simulation |
| F-18/F-19 answer/feedback | Phase 3 training | Port | Blame-free, immediate, group-level reporting |
| F-20 score | Phase 3 analytics | Replace | Learning progress, not punitive ranking |
| F-21/F-22 analyzer | Phase 4 analyzer | Port | Add API, consent, rate limits, no raw-content retention |
| F-23 Gmail paste | Phase 4 analyzer | Port | Paste path with size limits and explicit consent |
| F-24 `.eml` upload | Phase 4 analyzer | Port | 5 MB limit; no storage by default; malware-safe parsing |
| F-25 header analysis | `ml/` + backend | Port | dnspython/ARC support later; explainable reasons |
| F-26 link analysis | `ml/` | Port and extend | tldextract, Levenshtein, homoglyphs, punycode, blocklist |
| F-27 attachment analysis | `ml/` | Port | Filename/type checks; never execute or open attachments |
| F-28 action advice | content file | Port | Plain language; one content source |
| F-29 prevention layers | content/training | Port | Keep static guidance, add just-in-time tips |
| F-30 habits checklist | Phase 3 training | Port | Optional, private, not used for scoring |
| F-31/F-32 attack visualization | frontend content | Port | Respect reduced motion; text alternative |
| F-33 theme | design system | Replace | Light/dark tokens from `docs/design-system.md` |
| F-34 responsive | design system | Replace | 320px minimum, 200% zoom |
| F-35 escaping | frontend/backend | Keep principle | Framework escaping plus sanitization for email HTML |
| F-36 local-only | architecture | Replace | Server-side sessions, explicit network boundaries |
| `EMP` | `targets`, `groups`, `users` | Replace | Real org data with minimal fields; employee accounts separate |
| `DEPTS` | group/department field | Replace | Flexible groups, not fixed four departments |
| `SC` | `templates`, `template_red_flags` | Port | Versioned; add SC-09/SC-10; no real brands/logos |
| `SC.ind` | `template_red_flags` / trainer copy | Port | Shown in preview and awareness |
| `camps` | `campaigns`, `campaign_targets`, `authorizations` | Replace | Server-side state, approval gate, scheduling |
| `res` | `events` | Replace | Append-only, tokenized, minimized |
| `score`/`stats`/`dpPanel` | reporting services | Port logic, replace storage | Group-level, retention-aware, audited |
| `scan` | `ml/rules` + `/analyzer` | Port | Rule IDs S-01…S-15 become regression tests |
| `emlText` | `ml/` parser + `/analyzer` | Port | Rule IDs E-01…E-12; MIME edge cases tracked |
| `ORG` | `organizations.domain` | Replace | Settings-managed, validated |
| `localStorage["psim"]` | PostgreSQL | Remove | No campaign results in browser storage |
| `tips`/`PREV`/`CHK` | `frontend/src/content` | Port | One content file; glossary from design system |
| `esc()` / CSV quote | shared utilities | Keep principle | Server-side output encoding and CSV hardening |
| `security-check.sh` | CI + security tests | Replace | SAST, secrets, dependency, authz and header tests |
| `test.js` | pytest + Playwright | Replace | Rule fixtures, API tests, accessibility tests |
| CSP `default-src 'none'` | deployment headers | Replace | Strict CSP compatible with Next.js; no inline scripts |
| Fake-login HTML | awareness component | Port | Labelled simulation only; `form_touched` on focus/first input, never values or keystrokes |

---

## 9. Non-negotiable porting decisions

1. **No fabricated behaviour.** The random `simulate()` answers are not ported. Metrics come from real events.
2. **No client-side results.** Campaign state and results are server-side; the browser does not own scoring.
3. **No credential handling.** Even disabled inputs are replaced by a clear explanatory panel or a simulated form. A simulated field fires `form_touched` on focus or first input, never reads its value, never logs keystrokes, and is visibly labelled as a simulation. No real credentials are requested or accepted.
4. **No real brands or domains.** Legacy `paypa1`, `dhl`, and `company-docs` examples are training references only; production templates use sanctioned fictional brands or the organization's own sandbox domain.
5. **No raw email retention.** Analyzer input is processed for the response and only minimized metadata is stored (see assumptions).
6. **Group-level reporting is the default.** Individual detail requires admin access and a logged reason.
7. **Rules become versioned tests.** S-01…S-15, E-01…E-12 and T-01…T-10 must have equivalents before Phase 4 is complete.
8. **Legacy stays frozen.** Proposed scenarios SC-09/SC-10 live in documentation and the new seed data, not in `legacy/index.html`.

---

## 10. Traceability checklist

- [ ] S-01…S-15 implemented with unit fixtures.
- [ ] E-01…E-12 implemented with parser fixtures.
- [ ] T-01…T-10 mapped to pytest and/or Playwright tests.
- [ ] SC-01…SC-08 seeded without real brands; SC-09/SC-10 added for ATT&CK coverage.
- [ ] `form_touched` fires only on focus/first input, never reads values or keystrokes, and the field is labelled as a simulation.
- [ ] CSV export formula-injection test ported.
- [ ] Group suppression below five members tested.
- [ ] Retention deletion tested.
- [ ] Legacy test and security commands still pass from the repo root.
