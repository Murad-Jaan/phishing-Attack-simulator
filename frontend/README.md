# Frontend

Next.js (React) + Tailwind CSS + shadcn/ui application for the Phishing Attack Simulator.

**Status:** Phase 2+ — not implemented. Phase 1 is documentation-only.

## Rules

- Build only from the tokens, components and content rules in [`../docs/design-system.md`](../docs/design-system.md).
- Keep all UI strings in one content file (planned: `src/content/en.ts`) so they can be reviewed and translated together.
- Use shadcn/ui (Radix primitives) for dialogs, menus, tabs, tooltips, toasts and form controls; do not hand-roll them.
- Every page must implement empty, loading, error and success states, full keyboard use, visible focus and WCAG 2.2 AA contrast.
- Never render user or email content without escaping. Never collect credentials.
- Do not duplicate legacy code from [`../legacy/`](../legacy/); port behaviour through the API and documented components.

## Planned structure

```
src/app/          routes for login, dashboard, campaigns, templates, groups,
                  preview, awareness, training, reports, analyzer, report, settings
src/components/   design-system components and page composition
src/content/      all UI strings
src/lib/          API client, session/CSRF handling, formatting
e2e/              Playwright tests, including axe-core checks
```

## Documentation

Start with [`../docs/architecture.md`](../docs/architecture.md), [`../docs/hci-and-wireframes.md`](../docs/hci-and-wireframes.md) and [`../docs/phase-2-checklist.md`](../docs/phase-2-checklist.md).
