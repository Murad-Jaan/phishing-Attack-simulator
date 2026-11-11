"""Dev-only seed data for the M4 template library.

All scenarios are fictional, use sandbox domains only, contain no real brands
or logos and never include a credential form. SC-01..SC-08 mirror the legacy
scenario intents; SC-09 and SC-10 add the proposed service-channel and
phishing-for-information coverage without editing the frozen legacy app.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.template import (
    Template,
    TemplateDifficulty,
    TemplateRedFlag,
    TemplateStatus,
)

SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "SC-01: Account suspension warning",
        "sender": "Account Security <security@account-verify.example.test>",
        "subject": "URGENT: Your account will be suspended!",
        "body": (
            "Dear customer,\n\n"
            "We detected unusual activity. Your account will be suspended within "
            "24 hours unless you confirm your details immediately.\n\n"
            "Verify your account: https://account-verify.example.test/login\n\n"
            "Account Security Team"
        ),
        "difficulty": TemplateDifficulty.EASY,
        "attack_technique_id": "T1566.002",
        "lure_type": "credential_harvest",
        "red_flags": [
            (
                "Urgency and threat",
                "The message creates a 24-hour deadline and threatens suspension "
                "to pressure the reader into acting.",
            ),
            (
                "Lookalike sender domain",
                "The sender uses a lookalike sandbox domain instead of the "
                "organization's own domain.",
            ),
            (
                "Generic greeting",
                "A generic greeting such as 'Dear customer' is a common sign of "
                "a bulk phishing message.",
            ),
            (
                "Credential-harvesting link",
                "The link points to an unfamiliar sign-in page that asks the "
                "reader to verify account details.",
            ),
        ],
    },
    {
        "name": "SC-02: Team lunch invitation",
        "sender": "HR Team <hr@example.test>",
        "subject": "Team lunch this Friday",
        "body": (
            "Hello {{first_name}},\n\n"
            "We are organizing a team lunch this Friday at 12:30 in the usual "
            "meeting room. Reply if you have any dietary requirements.\n\n"
            "Thanks,\nHR Team"
        ),
        "difficulty": TemplateDifficulty.EASY,
        "attack_technique_id": "none",
        "lure_type": "benign_control",
        "red_flags": [],
    },
    {
        "name": "SC-03: Invoice attachment",
        "sender": "Vendor Billing <accounts@vendor-billing.example.test>",
        "subject": "Invoice #8841 attached",
        "body": (
            "Dear {{first_name}},\n\n"
            "Please find attached invoice #8841 for last month's services. "
            "Payment is due today to avoid a late fee.\n\n"
            "The attachment is named invoice_8841.pdf.exe. Open it to view the "
            "amount and payment instructions.\n\n"
            "Vendor Billing"
        ),
        "difficulty": TemplateDifficulty.MEDIUM,
        "attack_technique_id": "T1566.001",
        "lure_type": "malicious_attachment",
        "red_flags": [
            (
                "Double file extension",
                "The attachment name ends in .pdf.exe. The real file type is an "
                "executable, not a PDF.",
            ),
            (
                "Unknown vendor",
                "The sender is an external billing address the reader may not "
                "recognize.",
            ),
            (
                "Payment pressure",
                "A same-day payment deadline is used to rush the reader into "
                "opening the attachment.",
            ),
        ],
    },
    {
        "name": "SC-04: Weekend maintenance notice",
        "sender": "IT Operations <it@example.test>",
        "subject": "Scheduled maintenance on Sunday",
        "body": (
            "Hello {{first_name}},\n\n"
            "IT Operations will perform scheduled maintenance on Sunday between "
            "02:00 and 04:00. Some internal services may be briefly unavailable.\n\n"
            "No action is required. Normal access will resume after the window.\n\n"
            "IT Operations"
        ),
        "difficulty": TemplateDifficulty.MEDIUM,
        "attack_technique_id": "none",
        "lure_type": "benign_control",
        "red_flags": [],
    },
    {
        "name": "SC-05: Confidential CEO favour",
        "sender": "CEO Office <ceo.office@mail.example.test>",
        "subject": "Quick favour - keep confidential",
        "body": (
            "Hi {{first_name}},\n\n"
            "I am in meetings all day and need a quick favour. Please purchase "
            "two gift cards for a client thank-you and send me the codes. Keep "
            "this confidential and do not call me about it.\n\n"
            "I will reimburse you as soon as I am back.\n\n"
            "CEO Office"
        ),
        "difficulty": TemplateDifficulty.MEDIUM,
        "attack_technique_id": "T1566",
        "lure_type": "bec_impersonation",
        "red_flags": [
            (
                "Executive impersonation",
                "A message claiming to be from a senior leader arrives from an "
                "external mailbox rather than the organization's own domain.",
            ),
            (
                "Gift-card request",
                "Requests to buy gift cards and share the codes are a classic "
                "business email compromise pattern.",
            ),
            (
                "Secrecy pressure",
                "The sender asks the reader to keep the request confidential and "
                "avoid verifying it by phone.",
            ),
        ],
    },
    {
        "name": "SC-06: Shared salary review",
        "sender": "Document Service <noreply@company-docs.example.test>",
        "subject": "Shared with you: Q3 Salary Review",
        "body": (
            "Hello {{first_name}},\n\n"
            "A file has been shared with you: Q3 Salary Review.\n\n"
            "Open the file: https://company-docs.example.test/shared/q3-salary\n\n"
            "You may need to re-authenticate to view this document.\n\n"
            "Document Service"
        ),
        "difficulty": TemplateDifficulty.HARD,
        "attack_technique_id": "T1566.002",
        "lure_type": "file_share",
        "red_flags": [
            (
                "Lookalike document domain",
                "The file-sharing domain imitates an internal document service "
                "but is not the organization's real domain.",
            ),
            (
                "Curiosity lure",
                "A salary review subject uses sensitive, interesting content to "
                "encourage a quick click.",
            ),
            (
                "Re-authentication request",
                "The link asks the reader to sign in again on an unfamiliar page.",
            ),
        ],
    },
    {
        "name": "SC-07: Password expiry notice",
        "sender": "IT Operations <it@example.test>",
        "subject": "Password expires in 7 days",
        "body": (
            "Hello {{first_name}},\n\n"
            "Your network password expires in 7 days. Use the normal self-service "
            "portal or contact the IT service desk if you need help.\n\n"
            "This notice was sent from the internal IT systems.\n\n"
            "IT Operations"
        ),
        "difficulty": TemplateDifficulty.HARD,
        "attack_technique_id": "none",
        "lure_type": "benign_control",
        "red_flags": [],
    },
    {
        "name": "SC-08: Parcel reschedule notice",
        "sender": "Delivery Updates <delivery@parcel-tracking.example.test>",
        "subject": "Package delivery failed - reschedule",
        "body": (
            "Hello {{first_name}},\n\n"
            "We could not deliver your parcel. A small rescheduling fee is "
            "required to arrange a new delivery date.\n\n"
            "Reschedule here: https://parcel-tracking.example.test/reschedule\n\n"
            "Delivery Updates"
        ),
        "difficulty": TemplateDifficulty.HARD,
        "attack_technique_id": "T1566.002",
        "lure_type": "package_delivery",
        "red_flags": [
            (
                "Unexpected parcel",
                "The reader is not expecting a delivery and cannot match it to a "
                "known order.",
            ),
            (
                "Unofficial domain",
                "The tracking domain is not an official carrier domain and uses "
                "a generic parcel-tracking name.",
            ),
            (
                "Payment link",
                "A rescheduling fee is used to move the reader to a payment page.",
            ),
        ],
    },
    {
        "name": "SC-09: Shared workspace document",
        "sender": "Workspace <share@workspace.example.test>",
        "subject": "A document was shared with you",
        "body": (
            "Hi {{first_name}},\n\n"
            "A document was shared with you in the team workspace. Open the "
            "workspace to review it.\n\n"
            "Open document: https://workspace.example.test/s/abc123\n\n"
            "Workspace"
        ),
        "difficulty": TemplateDifficulty.MEDIUM,
        "attack_technique_id": "T1566.003",
        "lure_type": "service_share",
        "red_flags": [
            (
                "Third-party service delivery",
                "The lure arrives through a simulated collaboration service rather "
                "than the organization's normal communication channel.",
            ),
            (
                "Unexpected share",
                "The reader is not expecting a document from this service.",
            ),
            (
                "Consent screen",
                "The link leads to a simulated consent screen that requests access "
                "to the account.",
            ),
        ],
    },
    {
        "name": "SC-10: Service desk identity check",
        "sender": "IT Service Desk <servicedesk@it-help.example.test>",
        "subject": "Ticket #4021: confirm your identity",
        "body": (
            "Hello {{first_name}},\n\n"
            "We are closing ticket #4021. To confirm ownership, reply with your "
            "employee ID and a contact phone number.\n\n"
            "If we do not hear back today, the ticket will be reopened and may "
            "delay your access request.\n\n"
            "IT Service Desk"
        ),
        "difficulty": TemplateDifficulty.MEDIUM,
        "attack_technique_id": "T1598",
        "lure_type": "phishing_for_information",
        "red_flags": [
            (
                "Unexpected identity request",
                "The sender asks for employee and contact details that the real "
                "service desk would not request by email.",
            ),
            (
                "Ticket pressure",
                "A same-day deadline pressures the reader to reply without "
                "verifying the request through a known channel.",
            ),
            (
                "External help-desk domain",
                "The message comes from an external help-desk domain rather than "
                "the organization's internal IT address.",
            ),
        ],
    },
]


def seed_templates(db: Session, org: Organization) -> int:
    """Insert missing scenario templates for the demo org. Idempotent."""
    inserted = 0
    for scenario in SCENARIOS:
        existing = db.execute(
            select(Template).where(
                Template.org_id == org.id,
                Template.name == scenario["name"],
                Template.is_demo.is_(True),
            )
        ).scalar_one_or_none()
        if existing is not None:
            continue
        template = Template(
            org_id=org.id,
            name=scenario["name"],
            sender=scenario["sender"],
            subject=scenario["subject"],
            body=scenario["body"],
            difficulty=scenario["difficulty"],
            attack_technique_id=scenario["attack_technique_id"],
            lure_type=scenario["lure_type"],
            status=TemplateStatus.PUBLISHED,
            is_demo=True,
        )
        for label, explanation in scenario["red_flags"]:
            template.red_flags.append(
                TemplateRedFlag(label=label, explanation=explanation)
            )
        db.add(template)
        inserted += 1
    db.flush()
    return inserted
