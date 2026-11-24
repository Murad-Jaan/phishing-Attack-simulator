# Design System and Content Baseline

Phishing Simulation + Detection platform. This file is the source of truth for UI and copy. Rules come from `docs/PLAN.md` (Nielsen's 10 heuristics, Shneiderman's 8 golden rules, Hick's and Fitts's laws, WCAG 2.2 AA, explainable security).

## 1. Baseline decisions

| Layer | Baseline |
|---|---|
| Standards | WCAG 2.2 AA; Nielsen and Shneiderman as review checklists |
| Components | Tailwind CSS + shadcn/ui (Radix primitives). Do not hand-roll dialogs, menus, tabs, tooltips, toasts or form controls |
| Visual identity | Modern, calm, light/dark. A cool indigo primary with a violet-to-cyan gradient accent on airy cool-white (light) and deep midnight-navy (dark) surfaces; gradient and aurora tokens are decorative only, never used for meaning or text |
| Type | Inter, with a system-font fallback stack |
| Grid and spacing | 4px base unit, 8px rhythm |
| Targets | 44x44px minimum touch/click targets; large, close primary actions (Fitts's law) |
| Meaning | Never color alone. Every status has an icon and a text label |
| Language | Plain, non-punitive, explains why and what to do next |

## 2. Color tokens

All text pairs must be at least 4.5:1 (normal text) and UI boundaries/icons at least 3:1. Ratios below were computed with the WCAG relative-luminance formula.

### Light theme

| Token | Hex | Use |
|---|---|---|
| `--bg` | #F4F7FC | Page background |
| `--surface` | #FFFFFF | Cards, dialogs, inputs |
| `--surface-muted` | #EDF1F9 | Muted panels, table headers, ghost hover |
| `--border` | #DCE3F0 | Decorative dividers and card borders |
| `--control-border` | #7C8AA5 | Form and button boundaries (3.24:1 on bg, 3.48:1 on surface) |
| `--text` | #0F172A | Body and headings |
| `--text-muted` | #55617A | Secondary text and helper copy |
| `--text-strong-muted` | #33405C | Nav items, table headers |
| `--primary` | #4F46E5 | Primary button and icon fills |
| `--primary-hover` | #4338CA | Primary fill hover |
| `--on-primary` | #FFFFFF | Text and icons on primary |
| `--primary-strong` | #3730A3 | Links, active nav text, focus ring |
| `--primary-tint` | #E9EDFF | Active nav, selected rows |
| `--primary-tint-border` | #C7CCFF | Tinted borders |
| `--danger` | #D61E46 | Destructive button fill |
| `--danger-hover` | #BE123C | Destructive fill hover |
| `--on-danger` | #FFFFFF | Text and icons on danger |
| `--danger-strong` | #BE123C | Risk text, invalid borders, danger icons |
| `--danger-tint` | #FFE4EA | Risk badges and alerts |
| `--danger-tint-border` | #FECDD3 | Risk alert and badge borders |
| `--success` | #047857 | Safe, reported, completed text and icons |
| `--success-tint` | #E6FBF2 | Safe badges and alerts |
| `--success-tint-border` | #A7F3D0 | Safe alert and badge borders |
| `--warning` | #92400E | Caution text and icons |
| `--warning-tint` | #FEF7E6 | Caution badges and alerts |
| `--warning-tint-border` | #FDE68A | Caution alert and badge borders |

### Dark theme

| Token | Hex | Use |
|---|---|---|
| `--bg` | #0A0E1A | Page background |
| `--surface` | #121826 | Cards, dialogs, inputs |
| `--surface-muted` | #0E1424 | Muted panels, table headers, ghost hover |
| `--border` | #243049 | Decorative dividers and card borders |
| `--control-border` | #64748B | Form and button boundaries (3.73:1 on surface, 4.05:1 on bg) |
| `--text` | #F7F2F3 | Body and headings |
| `--text-muted` | #A8B3C7 | Secondary text and helper copy |
| `--text-strong-muted` | #CBD5E6 | Nav items, table headers |
| `--primary` | #818CF8 | Primary button and icon fills |
| `--primary-hover` | #A5B4FC | Primary fill hover |
| `--on-primary` | #0B1020 | Text and icons on primary |
| `--primary-strong` | #A5B4FC | Links, active nav text, focus ring |
| `--primary-tint` | #1B2140 | Active nav, selected rows |
| `--primary-tint-border` | #38407A | Tinted borders |
| `--danger` | #FB7185 | Destructive button fill |
| `--danger-hover` | #FDA4AF | Destructive fill hover |
| `--on-danger` | #2A0510 | Text and icons on danger |
| `--danger-strong` | #FDA4AF | Risk text, invalid borders, danger icons |
| `--danger-tint` | #2A1220 | Risk badges and alerts |
| `--danger-tint-border` | #5A2338 | Risk alert and badge borders |
| `--success` | #6EE7B7 | Safe, reported, completed text and icons |
| `--success-tint` | #0C2A24 | Safe badges and alerts |
| `--success-tint-border` | #1E5A4A | Safe alert and badge borders |
| `--warning` | #FCD34D | Caution text and icons |
| `--warning-tint` | #2A2210 | Caution badges and alerts |
| `--warning-tint-border` | #5A4A18 | Caution alert and badge borders |

Decorative-only tokens (never used for text or status): `--accent-cyan`, `--accent-violet`, `--accent-glow`, `--primary-gradient`, `--accent-gradient`, `--aurora-a`, `--aurora-b`, `--aurora-c`, `--grid-line`. They power the aurora background, gradient logo, focus/hover glows, accent bars and button sheen.

### Verified text contrast

Minimum ratio across every background the token is used on:

| Foreground token | Backgrounds used | Light | Dark |
|---|---|---|---|
| `--text` | bg, surface, surface-muted, tints | 14.91 | 13.81 |
| `--text-muted` | bg, surface, surface-muted, tints | 5.19 | 7.24 |
| `--text-strong-muted` | bg, surface, surface-muted | 9.14 | 11.99 |
| `--primary-strong` | bg, surface, primary-tint | 8.52 | 7.87 |
| `--danger-strong` | bg, surface, danger-tint | 5.25 | 9.21 |
| `--success` | bg, surface, success-tint | 5.08 | 10.04 |
| `--warning` | bg, surface, warning-tint | 6.60 | 10.91 |
| `--on-primary` | primary | 6.29 | 6.35 |
| `--on-danger` | danger | 5.08 | 6.92 |

Spot checks for the most common pairs:

| Pair | Light | Dark |
|---|---|---|
| `--text` on `--bg` | 16.63 | 17.38 |
| `--text` on `--surface` | 17.85 | 16.00 |
| `--text-muted` on `--bg` | 5.79 | 9.11 |
| `--text-muted` on `--surface` | 6.22 | 8.39 |
| `--primary-strong` on `--primary-tint` | 8.52 | 7.87 |
| `--danger-strong` on `--danger-tint` | 5.25 | 9.21 |
| `--success` on `--success-tint` | 5.08 | 10.04 |
| `--warning` on `--warning-tint` | 6.64 | 10.91 |
| `--on-primary` on `--primary` | 6.29 | 6.35 |
| `--on-danger` on `--danger` | 5.08 | 6.92 |

Non-text contrast: `--control-border` is 3.24:1 light on the page and 3.48:1 light on the card surface; 4.05:1 dark on the page and 3.73:1 dark on the card surface. The focus ring (`--primary-strong`) is 9.25:1 light on the page and 9.93:1 light on the card surface; 9.66:1 dark on the page and 8.89:1 dark on the card surface. Do not use `--control-border` or `--border` for text; they are for boundaries only.

Rule: re-run the contrast check whenever a token changes, and keep the ratios in this file up to date. Respect `prefers-color-scheme` and offer a manual toggle.

## 3. Typography

Font stack: `Inter, system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif`.

| Style | Size / line height | Weight | Use |
|---|---|---|---|
| Display | 30 / 38 | 700 | Page titles |
| Heading 1 | 24 / 32 | 700 | Section titles |
| Heading 2 | 18 / 26 | 600 | Card titles |
| Body | 16 / 24 | 400 | Default text (never below 14px for body copy) |
| Small | 14 / 20 | 400-500 | Table cells, helper text |
| Caption | 12 / 16 | 500 | Badges, chart labels (not for essential instructions) |
| Metric | 36-40 / 44 | 700 | Dashboard key numbers |

Text must reflow and stay usable at 200% zoom and with user font-size changes. Use rem units.

## 4. Spacing, layout and shape

- Spacing scale: 4, 8, 12, 16, 24, 32, 48, 64.
- Radius: 10px (controls), 16px (cards), 999px (badges).
- Desktop: left sidebar 240px, content max width 1136px. Tablet and mobile: sidebar collapses into a menu button.
- Cards separated by 24px; padding 24px.
- Breakpoints: 640, 768, 1024, 1280.
- No horizontal page scroll; wide tables scroll inside their own container.
- Hick's law: no screen has more than one primary action; group secondary actions in a menu.

## 5. Components

Build on shadcn/ui and keep one variant set.

| Component | Rules |
|---|---|
| Button | Variants: primary, secondary, ghost, destructive. Min height 44px. Loading state with text ("Sending..."), never a spinner alone |
| Input, Select, Textarea | Visible label always (no placeholder-only labels), helper text, inline error text linked with `aria-describedby` |
| Table | Sortable headers as buttons, row actions reachable by keyboard, scroll container labelled |
| Card | One title, one purpose |
| Badge | Icon + text + tint (for example check icon + "Safe") |
| Alert | Types: info, success, warning, danger; icon + title + what to do |
| Dialog | Focus trapped, closes with Esc, returns focus to the trigger; used for confirmations of risky actions |
| Tabs, Dropdown, Tooltip | Radix behavior unchanged; tooltips never hold essential info |
| Toast | Polite live region; stays at least 6 seconds; has an Undo action when possible |
| Stepper | Used in the Campaign Creator; shows "Step 2 of 5", lets users go back |
| Charts | Always paired with a data table or text summary; patterns or labels in addition to color |
| Empty state | Explains what belongs here and offers the next action |
| Skeleton | For loading states over 300ms |

## 6. Status and risk language

| State | Icon | Label | Colors |
|---|---|---|---|
| Safe | check-circle | "Low risk" | success |
| Caution | alert-triangle | "Suspicious" | warning |
| Risk | shield-alert | "Likely phishing" | danger |
| Running | play-circle | "Running" | primary |
| Draft | pencil | "Draft" | muted |
| Completed | check | "Completed" | success |
| Paused | pause-circle | "Paused" | warning |

Red always means risk, green always means safe, blue always means action. Never reuse them for anything else.

## 7. Interaction rules

- **Visibility of status:** show progress for scheduled sends ("Queued, Sent, Opened, Clicked, Reported") and live counters.
- **User control:** pause, cancel, undo draft changes, easy exit from training.
- **Error prevention:** launch checklist, authorization confirmation, test send, confirm dialogs that name what will happen ("Send to 120 people").
- **Recognition over recall:** saved groups, template gallery with previews, dropdowns instead of free text.
- **Efficiency:** keyboard shortcuts, bulk CSV import, filters; shortcuts are discoverable in a help dialog.
- **Motion:** Functional transitions 150-320ms (page enter, cards, toasts, buttons). Ambient decorative motion (slow aurora blobs, accent-bar gradient pan, button sheen) is non-informational, low-contrast, and carried by decorative-only tokens. A single global `prefers-reduced-motion: reduce` override disables every animation and transition, including the ambient layers; verify with `tests/reduced-motion.spec.ts`.
- **Timeouts:** warn before any session timeout and allow extension.

## 8. Accessibility checklist (every page)

- One `h1`, logical heading order, landmarks (`header`, `nav`, `main`).
- Skip link to main content.
- Full keyboard use, visible focus ring (2px, 3:1 against adjacent colors), no keyboard traps.
- Labels, names and states for all controls; ARIA only where native HTML is not enough.
- Form errors announced and linked to fields; do not clear user input on error.
- Alt text for informative images; decorative images hidden from assistive tech.
- Link and button text makes sense out of context ("View report for HR policy update").
- Touch targets at least 44x44px (WCAG 2.2 target size).
- Works at 200% zoom and 320px width.
- Run axe-core in Playwright for every page; fix all serious and critical issues.

## 9. Content guidelines

### Voice
- Plain language, about a grade 8 reading level; short sentences; active voice.
- Calm and respectful. Never blame, shame or joke about people who clicked.
- Use words employees already know: "fake sender address", not "spoofed envelope".

### Fixed glossary
| Term | Meaning |
|---|---|
| Campaign | A scheduled run of one template sent to one group |
| Template | A simulated email (or message) with its red flags |
| Group | A named list of targets |
| Target | A person receiving a simulation |
| Simulation | A safe, authorized practice phishing message |
| Report | A target flagging a message as suspicious |
| Analyzer | The tool that scores real emails |

Use one term per concept everywhere. Keep all UI strings in one file (for example `frontend/src/content/en.ts`) so they can be translated later (for example into Urdu) and reviewed together.

### Message patterns

**Errors:** say what happened, where, and how to fix it.
- Good: "Row 7 of your CSV has an invalid email address (ali@company). Fix it and upload again."
- Bad: "Invalid input."

**Warnings and flags:** say why, then what to do.
- Good: "This email may be fake. The sender's domain (paypa1-support.com) looks like PayPal but is not. Do not click the link. Report it to IT."
- Bad: "Dangerous email."

**Awareness page (shown after a click):**
- Title: "This was a phishing simulation"
- Body: "No harm done, and no information was saved. Here are the signs that gave it away."
- Then: highlighted red flags (icon + text), 3 tips, "Start 3-minute training".

**Confirmations naming impact:** "Send this campaign to 120 people in Finance on 12 Nov at 10:00?" with buttons "Send campaign" and "Go back".

**Empty states:** "No campaigns yet. Create your first one to see results here." with a "New campaign" button.

**Success feedback:** "Campaign scheduled for 12 Nov at 10:00. You can pause it any time."

### Realism without risk
- Simulated lures may sound realistic, but use fake data, sandbox domains and no real brand logos.
- No real attachments, no real credential capture, no malware.
- Show the authorization and rules-of-engagement notice before launch.

## 10. Page-level requirements

| Page | Primary action | Must include |
|---|---|---|
| Login | Sign in | Clear error, password reveal, no credential hints |
| Dashboard | New campaign | 4 key numbers first, details on demand, table alternatives for charts |
| Campaign Creator | Next / Launch | Stepper, draft autosave, test send, authorization gate, review step |
| Template Library | Use template | Preview, difficulty tag, ATT&CK ID, red-flag list, search and filter |
| Target Groups | Add targets | CSV import with row-level errors, group-level reporting by default |
| Email Preview | Close preview | Desktop and mobile view, red-flag toggle |
| Awareness Page | Start training | Blame-free tone, under 3 minutes, no data collected |
| Training and Quiz | Submit answer | Progress, explanations for each answer, retry |
| Reports | Export | Funnel, trends, department comparison, table alternatives, CSV with formula-injection protection |
| Mail Analyzer | Analyze | Upload or paste, 0-100 score, label, "why was this flagged?", "What to do" |
| Report Phish | Report | One-click report, thank-you message, IT triage view |
| Settings | Save | Retention period, delete-all-data with confirmation, audit log view |

Every page needs defined empty, loading, error and success states.

## 11. Definition of done for UI work

- Uses tokens and components from this file only.
- All text pairs verified against the contrast table.
- Keyboard-only walkthrough completed.
- axe-core passes with no serious or critical issues.
- Copy follows the glossary and message patterns, and strings live in the content file.
- Tested in light and dark themes, at 320px width and 200% zoom.
- Matches the Nielsen and Shneiderman checklist in `docs/PLAN.md`.
