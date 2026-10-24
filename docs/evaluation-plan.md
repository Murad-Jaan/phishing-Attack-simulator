# Evaluation Plan

This plan covers Phase 1 acceptance criteria and the metrics used to validate effectiveness, detection quality, and usability. All data collection must follow [`ethics-and-consent.md`](ethics-and-consent.md).

---

## 1. Human performance metrics

| Metric | Definition | Target / Measurement | Data source |
|---|---|---|---|
| Click rate | (Targets who clicked a link / delivered targets) × 100 | **Delivered** = accepted by the receiving mail server (inbox placement is unknown). Tracked per group/campaign; compare against baseline with suppression (k≥5). Filter security-scanner and bot clicks (user agent, timing, repeated hits). | `events` (tokenized) |
| Report rate | (Targets who reported / delivered targets) × 100 | **Delivered** = accepted by the receiving mail server (inbox placement is unknown). Primary success metric; promote reporting without punishment. | `events` + triage |
| Time-to-report (primary) | Median time from **delivery** to report (seconds/minutes) | Primary timing metric. Report median and IQR. | Event timestamps |
| Time-to-report (secondary) | Median time from **click** to report (seconds/minutes) | Secondary only; not required if no click occurred. | Event timestamps |
| Repeat-clicker trend | % of targets who clicked on ≥2 campaigns within the evaluation window | Tracked over time (trend), not a public leaderboard. | `events` aggregated by target hash (pseudonymous) |

**Measurement validity:** `opened` is **unreliable** and is **not** a success metric. Only delivery, click, form_touched, answered, and reported events are considered reliable for evaluation. All clicks must be filtered for security-scanner/bot activity (user agent heuristics, timing anomalies, repeated hits from the same source in an implausible pattern).

---

## 2. Detector metrics (Mail Analyzer / rules)

Detection is evaluated against a **held-out set** not used for rule development or tuning.

| Metric | Definition | Target / Notes |
|---|---|---|
| Precision | TP / (TP + FP) | **needs decision** – propose ≥ 0.90 |
| Recall | TP / (TP + FN) | **needs decision** – propose ≥ 0.90 |
| F1 | 2*(P*R)/(P+R) | Report alongside precision/recall |
| False-positive rate (FPR) | FP / (FP + TN) | **needs decision** – propose ≤ 0.05; must be tracked on benign controls (SC-02, SC-04, SC-07) |

**Evaluation protocol:**
- **Splits:** train / validation / held-out test. Train for rule development; **threshold selection only on validation set**; final metrics reported on held-out test set.
- **Leakage controls:** deduplicate messages (exact + near-duplicate), enforce time separation where possible, enforce source separation, and ensure synthetic fixtures do not leak into held-out.
- **Confusion matrix:** report TP/FP/TN/FN per run.
- **Per-layer ablation:** test sender/header/content/link/attachment layers independently.
- **Regression:** legacy rule tests (S-01…S-15, E-01…E-12) must remain passing.

---

## 3. Dataset sources, licence checks

Emails are **never committed** to the repo. Only download scripts, a `datasets` manifest, and licence notes live in `ml/datasets/`.

| Dataset/source | Purpose | Licence / terms (to verify) | Action |
|---|---|---|---|
| **Nazario phishing corpus** (public) | Phishing samples for training/validation/held-out | **to verify** – check current terms of use, redistribution restrictions, and acceptable use before download. | Prefer access via approved source; document in manifest; no raw emails committed. |
| **SpamAssassin public corpus** | Spam and ham samples for comparison/FPR evaluation | **to verify** – check licence/terms; some versions have restrictions. The corpus contains both spam and ham, so it can serve as a ham source as well. | Only use if terms allow evaluation use; document restrictions. |
| **Ham source** (propose: Enron email dataset or synthetic benign) | Benign (ham) samples for FPR/benign controls | **to verify** – Enron has usage notes/considerations; must ensure no personal data misuse. Synthetic benign (SC-02/04/07 style) is preferred where possible. | Prefer synthetic benign; if using Enron, document provenance and redaction plan. |
| **Synthetic (SC-01–SC-10)** | Fixtures for rules/tests; supplement only | Project-created, no real brands. | Supplement, **do not** replace public data. |

**Required artifacts (not committed):**
- `ml/datasets/README.md` with download instructions
- `ml/datasets/manifest.json` (counts, hashes, sources, licence status)
- `ml/datasets/LICENSES.md` with verified licence text/links

---

## 4. Baseline, confidence intervals

- **Baseline campaign:** run a controlled baseline with an approved group before major changes. Use group-level reporting and suppression (k≥5).
- **Confidence intervals:** for groups of **5–10**, confidence intervals will be **wide**. Report point estimates with CIs (e.g. Wilson score interval) and explicitly state the small-sample uncertainty.
- **Pseudonymization:** targets aggregated by hash; no individual leaderboards.

---

## 5. Usability evaluation (SUS + task metrics)

| Metric | Definition | Target / Notes |
|---|---|---|
| Task success rate | % of participants who complete the defined tasks without critical failure | Report per task; include assistance if needed. |
| Time on task | Time to complete each task (seconds) | Report median/IQR. |
| Error rate | Errors / attempts or critical errors per task | Track recoverable vs critical errors. |
| SUS | Standard 10-item questionnaire | **SUS formula:** `SUS = 2.5 × (∑_{odd} (score_i - 1) + ∑_{even} (5 - score_i))`. Score range **0–100**. Target **≥ 80** (good/excellent). |

**SUS procedure:** 5–8 participants, representative roles, post-task administration. No performance ranking published. Findings used for usability/accessibility only.