# Design System and Content Baseline

Phishing Simulation + Detection platform. This file is the source of truth for UI and copy. Rules come from `docs/PLAN.md` (Nielsen's 10 heuristics, Shneiderman's 8 golden rules, Hick's and Fitts's laws, WCAG 2.2 AA, explainable security).

## 1. Baseline decisions

| Layer | Baseline |
|---|---|
| Standards | WCAG 2.2 AA; Nielsen and Shneiderman as review checklists |
| Components | Tailwind CSS + shadcn/ui (Radix primitives). Do not hand-roll dialogs, menus, tabs, tooltips, toasts or form controls |
| Visual identity | Clean, calm, light/dark. Tokens below come from the Figma home page and the legacy CSS variables |
| Type | Inter, with a system-font fallback stack |
| Grid and spacing | 4px base unit, 8px rhythm |
| Targets | 44x44px minimum touch/click targets; large, close primary actions (Fitts's law) |
| Meaning | Never color alone. Every status has an icon and a text label |
| Language | Plain, non-punitive, explains why and what to do next |

## 2. Color tokens

All text pairs must be at least 4.5:1 (normal text) and UI boundaries/icons at least 3:1. Ratios below were computed with the WCAG relative-luminance formula.

### Light theme

| Token | Hex | Use | Contrast check |
|---|---|---|---|
| `--bg` | #F6F7FB | Page background | n/a |
| `--surface` | #FFFFFF | Cards, dialogs | n/a |
| `--border` | #E5E8F0 | Dividers, card borders | decorative |
| `--text` | #14182B | Body and headings | 17.57:1 on white, 16.41:1 on bg |
| `--text-muted` | #5F667D | Secondary text | 5.70:1 on white, 5.33:1 on bg |
| `--text-strong-muted` | #4A5169 | Nav items, table headers | 7.86:1 on white |
| `--primary` | #2F5BEA | Primary buttons, links, focus | 5.52:1 with white text; 5.52:1 on white |
| `--primary-tint` | #EAF0FF | Active nav, selected rows | #2F5BEA on tint 4.84:1 |
| `--danger` | #C62828 | Risk, destructive buttons | white on #C62828 5.62:1 |
| `--danger-tint` | #FDECEC | Risk badges and alerts | #A61E1E on tint 6.51:1 |
| `--success` | #17703A | Safe, reported, completed | 6.15:1 on white |
| `--success-tint` | #E6F6EC | Safe badges and alerts | #17703A on tint 5.49:1 |
| `--warning` | #855500 | Caution text | 6.37:1 on white |
| `--warning-tint` | #FFF3DC | Caution badges and alerts | #855500 on tint 5.80:1 |

Do not use #8A91A8 (3.14:1 on white) or #6B728A on tinted or gray backgrounds for text. They are for disabled or decorative use only.

### Dark theme

| Token | Hex | Use | Contrast check |
|---|---|---|---|
| `--bg` | #0F1521 | Page background | n/a |
| `--surface` | #18212F | Cards, dialogs | n/a |
| `--border` | #2A3649 | Dividers | decorative |
| `--text` | #E8EDF6 | Body and headings | 15.55:1 on bg |
| `--text-muted` | #98A6BD | Secondary text | 7.42:1 on bg, 6.57:1 on surface |
| `--primary` | #6E93FF | Links, accents | 6.33:1 on bg, 5.61:1 on surface; button text #0F1521 on it 6.33:1 |
| `--danger` | #FF6B6B | Risk | 5.83:1 on surface |
| `--success` | #3EC06F | Safe | 6.92:1 on surface |
| `--warning` | #F0B429 | Caution | 8.68:1 on surface |

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
- Radius: 8px (controls), 14px (cards), 999px (badges).
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
- **Motion:** 150-250ms transitions; honor `prefers-reduced-motion`; no auto-playing animation longer than 5 seconds without a pause control.
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
