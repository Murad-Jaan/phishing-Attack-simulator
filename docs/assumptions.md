# Assumptions

All defaults below are the approved Phase 1 assumptions. Items marked **[needs decision]** require explicit approval before implementation. 

| Assumption | Value | Notes | Status |
|---|---|---|---|
| Retention | 90 days (configurable) | Enforced via a retention job. Deletion/anonymization is logged to audit. | Approved |
| Sandbox domains | `example.com`, `*.test`, `*.invalid` only | Hard allowlist for sending/simulation. No real brands or production domains. | Approved |
| Reporting scope | Group-level by default | Individual detail is not shown by default. | Approved |
| Group suppression | Groups below 5 members suppressed | Hard floor of 5. Admins can raise this value, but can **never** lower it below 5. | Approved |
| Individual detail access | Admin-only with logged reason | Must log actor, reason, scope, and timestamp to audit. | Approved |
| Authentication | Server-side sessions (HttpOnly, SameSite cookie) with CSRF protection | No client-side session state. CSRF tokens required for mutating requests. | Approved |
| Target data | Minimal fields only | No unnecessary PII. Import requires authorization reference. | Approved |
| `form_touched` | On focus or first input only | Never reads field value, never logs keystrokes. Field must be labelled as a simulation. | Approved |
| Test send | Creator's verified address or Mailpit sandbox inbox only | Never sent to the target group. | Approved |
| SC-09 delivery | Simulated sandbox chat/file-sharing service channel | Required for T1566.003 accuracy. | Approved |
| SC-05 mapping | T1566 (generic) with T1656 secondary | T1598 coverage must not rely on SC-05. | Approved |
| T1656 tactic | To be verified against current MITRE ATT&CK | **[needs verification]** Believed Defense Evasion, but must be confirmed against the version used for this project. | [needs verification] |
| SSO | Deferred to Phase 5 | Password sessions are enough through Phase 4 | Approved |
| Mail delivery | Mailpit only through Phase 5 | Any pilot SMTP relay needs a separate approved decision | Approved |
| Seed data | Dev-only demo seed script | Must be clearly labelled demo events, never run in production, and excluded from real reporting. | Approved |
| URL fetching | Disabled in analyzer | No outbound requests from analyzer to submitted URLs. | Approved |
| Attachments | Parse-only, never executed | No opening/execution of attachments. | Approved |