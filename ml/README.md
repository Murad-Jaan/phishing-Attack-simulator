# ML and Detection

Explainable, layered phishing detection for real email: authentication, sender/domain, URL, content, attachments and HTML.

**Status:** Phase 4 — not implemented. Phase 1 is documentation-only.

## Rules

- Every score must include plain-language reasons, not just a label.
- Port and test the legacy rule behaviour from [`../legacy/index.html`](../legacy/index.html) before adding models. The inventory is in [`../docs/legacy-migration-map.md`](../docs/legacy-migration-map.md).
- Never train on real employee data or store raw analyzed messages by default.
- Check dataset licences and usage terms before use; record them in the model card.
- Evaluate on a held-out, leakage-free set and report precision, recall, F1 and false-positive rate.
- Keep model and rule versions for reproducibility.
- Do not use filter-evasion features; the detector is defensive only.

## Planned structure

```
src/
  rules/          authentication, sender/domain, URL, content, attachment, HTML
  features/       feature extraction and normalization
  models/         baselines (TF-IDF + logistic regression) and optional transformer
  scoring/        aggregation, thresholds, label mapping, explanations
  cli/            train, evaluate and analyze commands
tests/            rule fixtures, regression tests, metric tests
datasets/         licence notes only; no committed email corpora
```

## Documentation

Start with [`../docs/PLAN.md`](../docs/PLAN.md) section 4, [`../docs/architecture.md`](../docs/architecture.md) and [`../docs/evaluation-plan.md`](../docs/evaluation-plan.md).
