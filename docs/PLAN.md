# Phishing Simulation + Detection Project: Plan, Analysis and Build Prompt

## 1. Project concept

Build one platform with two halves that feed each other:

- **Offensive half (authorized red-team simulation):** safe, consented phishing campaigns that measure how people behave.
- **Defensive half (real-mail detection and prevention):** an analyzer that scores real emails, explains why they look risky, and helps people report them.
- **The loop:** simulation results show which lures work, which tunes the detector and the training. The detector's findings become new simulation templates.

That loop is what separates a strong project from a basic "send fake emails and count clicks" tool.

## 2. Offensive security framing (done responsibly)

Model the campaigns on real attacker behavior, mapped to MITRE ATT&CK: T1566.001 (attachment), T1566.002 (link), T1566.003 (via service), and T1598 (information-gathering phishing). Use a simple kill-chain view: recon, lure design, delivery, user action, awareness, and report.

The guardrails below should be built into the app and stated in the report:

- Written authorization and rules of engagement are required before a campaign can launch.
- Never capture real passwords. Record only that a form was touched.
- Send from controlled sandbox domains, and use a local mail catcher such as Mailpit during development.
- Keep data minimal and set a retention period.
- Use a non-punitive tone, and report results by group, not by shaming individuals.
- Include no malware, real attachments, or filter-evasion techniques.

## 3. HCI principles applied

| Principle | How it appears in the project |
|---|---|
| Visibility of system status (Nielsen) | Campaign progress, "queued/sent/clicked" states, live counters |
| Match with the real world | Email previews look like a real inbox; plain-language labels |
| User control and freedom | Pause, cancel, undo draft changes; easy exit from training |
| Consistency and standards | One button style, one color meaning (red = risk, green = safe) |
| Error prevention | Launch checklist, test-send, confirm dialogs for sending |
| Recognition over recall | Template gallery with thumbnails, saved groups, dropdowns |
| Flexibility and efficiency | Keyboard shortcuts, bulk CSV import, filters |
| Minimalist design | Dashboard shows 4 key numbers first, details on demand |
| Help users recover from errors | Clear messages, such as "CSV row 7: invalid email" |
| Help and documentation | Inline tooltips, a "why was this flagged?" panel |

Additional rules to apply:

- **Shneiderman's golden rules:** especially informative feedback and reducing short-term memory load.
- **Cognitive load:** use Hick's law (fewer choices per screen) and Fitts's law (large, close primary buttons).
- **Accessibility:** follow WCAG 2.2 AA, with contrast of at least 4.5:1, keyboard navigation, and no color-only meaning. Mark the red-flag highlights with icons as well as color.
- **Teachable-moment design:** the awareness page should appear immediately after a click, be short (under 3 minutes), and be blame-free.
- **Explainable security:** every warning says why ("sender domain registered 3 days ago"), not just "dangerous."

## 4. Detection and prevention for real mail

Use a layered, explainable scoring engine.

### Detection layers

1. **Authentication:** SPF, DKIM, DMARC, and ARC results from the headers, plus Reply-To vs From mismatch.
2. **Sender and domain:** lookalike detection (Levenshtein distance, homoglyphs such as rn/m and 0/o), domain age if available, free-mail pretending to be a company.
3. **URL analysis:** display text vs real href mismatch, shorteners, IP-based URLs, excessive subdomains, punycode, redirect chains, and checks against an offline blocklist.
4. **Content:** urgency, fear, and reward language; generic greeting; credential requests. Use a TF-IDF + logistic regression baseline, then optionally a transformer model.
5. **Attachments and HTML:** double extensions, macro-enabled Office types, hidden elements, embedded forms.
6. **Output:** a 0-100 risk score, a label (Safe, Suspicious, Likely phishing), and a plain-language list of reasons.

### Prevention layers

- A "Report phishing" button flow and an "external sender" banner.
- Recommendations for DMARC enforcement, MFA (preferably FIDO2 keys), and link rewriting or sandboxing.
- Quarantine suggestions and just-in-time tips.
- Targeted training for people who struggle with specific lures.

**Connecting to real mail:** use read-only access (IMAP, Gmail API, or Microsoft Graph) with explicit user consent. Analyze headers, URLs, and text, not full mailbox contents. Offer a simpler fallback of uploading an .eml file or pasting headers, which is also easier to demo.

## 5. Architecture and tools

- **Frontend:** React or Next.js with Tailwind, built from a Figma design system.
- **Backend:** Python FastAPI, PostgreSQL, Celery with Redis for scheduled sends.
- **Mail:** Mailpit for testing, with an SMTP relay for real pilots.
- **Detection libraries:** dnspython, tldextract, python-Levenshtein, scikit-learn, email/mailparser.
- **Datasets:** public phishing and ham corpora (such as the Nazario phishing corpus and SpamAssassin). Check each license and usage terms.

## 6. Analysis: risks, metrics and timeline

### Main risks

- Ethical or legal misuse, handled by authorization gates and logs.
- Privacy exposure from real-mail access, handled by consent and minimal data.
- Detector false positives, which erode trust, handled by showing reasons and allowing feedback.
- Training fatigue, handled by short, varied lessons.

### Metrics

- **Human:** click rate, report rate, time-to-report, repeat-clicker trend.
- **Detector:** precision, recall, F1, and false-positive rate on a held-out set.
- **HCI:** System Usability Scale (SUS), task completion time, and error rate from a test with 5-8 users.

### Suggested timeline (8-10 weeks)

1. Weeks 1-2: requirements, threat model, ethics rules, Figma wireframes.
2. Weeks 3-4: core platform (auth, groups, templates, campaigns).
3. Weeks 5-6: tracking, awareness page, training, reports.
4. Weeks 6-7: detection engine and mail analyzer.
5. Week 8: usability testing and fixes.
6. Weeks 9-10: evaluation, documentation, demo.
