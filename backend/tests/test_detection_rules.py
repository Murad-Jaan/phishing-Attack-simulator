from __future__ import annotations

from pathlib import Path

import pytest

from app.detection import analyze_eml, analyze_paste
from app.detection.analyzer import (
    LIKELY_PHISHING,
    SAFE,
    SUSPICIOUS,
)

ORG = "example.test"


def eml(headers: list[str], body: str) -> str:
    return "\n".join(headers) + "\n\n" + body


def rule_ids(result) -> list[str]:
    return [finding.rule_id for finding in result.findings]


CONTENT_CASES = [
    ("S-01", {"sender": "security@evil.test", "body": "Hello there."}),
    ("S-02", {"sender": "ceo.office@gmail.com", "body": "Please review the plan."}),
    ("S-03", {"sender": "security@paypa1-support.com", "body": "Hello there."}),
    ("S-04", {"sender": "billing@vendor-billing.test", "body": "Hello there."}),
    ("S-05", {"link": "http://example.test/portal"}),
    ("S-06", {"link": "http://198.51.100.7/portal"}),
    ("S-07", {"link": "https://bit.ly/abc123"}),
    ("S-08", {"link": "https://example.test@evil.test/portal"}),
    ("S-09", {"link": "https://other.test/portal"}),
    ("S-10", {"body": "Act now or the account will be suspended."}),
    ("S-11", {"body": "Please confirm your password."}),
    ("S-12", {"body": "Send a gift card code today."}),
    ("S-13", {"body": "Dear Customer, please review."}),
    ("S-14", {"body": "See Invoice_8841.pdf.exe attached."}),
    ("S-15", {"body": "Keep this confidential."}),
]


@pytest.mark.parametrize("expected,payload", CONTENT_CASES)
def test_content_rule_fixture(expected: str, payload: dict) -> None:
    input_payload = {"sender": "hr@example.test", **payload}
    result = analyze_paste(org_domain=ORG, **input_payload)
    assert expected in rule_ids(result)


def test_clean_message_scores_low() -> None:
    result = analyze_eml(
        eml(
            [
                "From: HR <hr@example.test>",
                "Authentication-Results: mx; spf=pass; dkim=pass; dmarc=pass",
                "Subject: Team lunch",
            ],
            "Lunch is on Friday at 1 PM.",
        ),
        org_domain=ORG,
    )
    assert result.score == 0
    assert result.label == SAFE
    assert result.rule_ids == []


def test_forged_header_message_scores_high() -> None:
    result = analyze_eml(
        eml(
            [
                'From: "PayPal" <service@paypa1-support.com>',
                "Reply-To: <collect@evil-mail.test>",
                "Return-Path: <bounce@other.test>",
                "Authentication-Results: mx; spf=fail; dkim=fail; dmarc=fail",
                "Subject: Urgent verify your password",
            ],
            '<a href="http://evil-login.test/x">https://paypal.com/login</a> '
            "verify your password within 24 hours",
        ),
        org_domain=ORG,
    )
    assert result.score >= 60
    assert result.label == LIKELY_PHISHING
    for expected in ("E-02", "E-03", "E-04", "E-05", "E-06", "E-07"):
        assert expected in rule_ids(result)


def test_sample_phishing_paste_is_high_risk() -> None:
    result = analyze_paste(
        sender="security@paypa1-support.com",
        link="http://paypa1-verify.com/login",
        subject="URGENT: Your account will be suspended!",
        body=(
            "Dear Customer, urgent: verify your password within 24 hours "
            "or your account will be suspended."
        ),
        org_domain="company.com",
    )
    assert result.score >= 60
    assert result.label == LIKELY_PHISHING


SCENARIOS = [
    (
        True,
        "security@paypa1-support.com",
        "URGENT: Your account will be suspended!",
        "Dear Customer, We detected unusual activity. Verify your account within 24 hours or it will be permanently closed.",
        "http://paypa1-verify.com/login",
        "",
    ),
    (
        False,
        "hr@company.com",
        "Team lunch this Friday",
        "Hi team, We are having a team lunch on Friday at 1 PM in the cafeteria.",
        "",
        "",
    ),
    (
        True,
        "accounts@vendor-billing.co",
        "Invoice #8841 attached",
        "Hello, Please find the overdue invoice attached and settle today to avoid penalties.",
        "",
        "Invoice_8841.pdf.exe",
    ),
    (
        False,
        "it@company.com",
        "Scheduled maintenance on Sunday",
        "The mail server will be down Sunday 2-4 AM for maintenance. No action is needed.",
        "",
        "",
    ),
    (
        True,
        "ceo.office@gmail.com",
        "Quick favor — keep confidential",
        "I need you to buy 5 gift cards for a client and send me the codes. I'm in a meeting so can't call.",
        "",
        "",
    ),
    (
        True,
        "noreply@company-docs.net",
        "Shared with you: Q3 Salary Review",
        "A colleague shared a document with you. Click to open and sign in to view.",
        "https://company-docs.net/view/q3",
        "",
    ),
    (
        False,
        "it@company.com",
        "Password expires in 7 days",
        "Your password expires in 7 days. You can change it anytime from the company SSO portal.",
        "https://sso.company.com/reset",
        "",
    ),
    (
        True,
        "delivery@dhl-tracking-pk.com",
        "Package delivery failed — reschedule",
        "We could not deliver your parcel. Pay a small fee of Rs. 150 to reschedule.",
        "http://dhl-tracking-pk.com/pay",
        "",
    ),
]


def test_ported_scenarios_separate_phishing_from_legitimate() -> None:
    phishing = []
    legitimate = []
    for is_phishing, sender, subject, body, link, attachment in SCENARIOS:
        text = f"{body} {attachment}".strip()
        result = analyze_paste(
            sender=sender,
            subject=subject,
            body=text,
            link=link,
            org_domain="company.com",
        )
        if is_phishing:
            phishing.append(result.score)
        else:
            legitimate.append(result.score)
    assert min(phishing) >= 30
    assert max(legitimate) < 30


def test_e01_missing_authentication_results() -> None:
    result = analyze_eml(
        eml(["From: HR <hr@example.test>", "Subject: Lunch"], "Lunch on Friday."),
        org_domain=ORG,
    )
    assert "E-01" in rule_ids(result)


def test_e02_spf_failure() -> None:
    result = analyze_eml(
        eml(
            [
                "From: HR <hr@example.test>",
                "Authentication-Results: mx; spf=fail; dkim=pass; dmarc=pass",
                "Subject: Lunch",
            ],
            "Lunch on Friday.",
        ),
        org_domain=ORG,
    )
    assert "E-02" in rule_ids(result)


def test_e03_dkim_failure() -> None:
    result = analyze_eml(
        eml(
            [
                "From: HR <hr@example.test>",
                "Authentication-Results: mx; spf=pass; dkim=fail; dmarc=pass",
                "Subject: Lunch",
            ],
            "Lunch on Friday.",
        ),
        org_domain=ORG,
    )
    assert "E-03" in rule_ids(result)


def test_e04_dmarc_failure() -> None:
    result = analyze_eml(
        eml(
            [
                "From: HR <hr@example.test>",
                "Authentication-Results: mx; spf=pass; dkim=pass; dmarc=fail",
                "Subject: Lunch",
            ],
            "Lunch on Friday.",
        ),
        org_domain=ORG,
    )
    assert "E-04" in rule_ids(result)


def test_e05_reply_to_mismatch() -> None:
    result = analyze_eml(
        eml(
            [
                "From: HR <hr@example.test>",
                "Reply-To: Collector <collect@evil.test>",
                "Authentication-Results: mx; spf=pass; dkim=pass; dmarc=pass",
                "Subject: Lunch",
            ],
            "Lunch on Friday.",
        ),
        org_domain=ORG,
    )
    assert "E-05" in rule_ids(result)
    assert result.parsed["reply_to"] == "collect@evil.test"


def test_e05_display_name_mismatch() -> None:
    result = analyze_eml(
        eml(
            [
                'From: "paypal.com Billing" <hr@example.test>',
                "Authentication-Results: mx; spf=pass; dkim=pass; dmarc=pass",
                "Subject: Lunch",
            ],
            "Lunch on Friday.",
        ),
        org_domain=ORG,
    )
    assert "E-05" in rule_ids(result)


def test_e06_return_path_mismatch() -> None:
    result = analyze_eml(
        eml(
            [
                "From: HR <hr@example.test>",
                "Return-Path: <bounce@other.test>",
                "Authentication-Results: mx; spf=pass; dkim=pass; dmarc=pass",
                "Subject: Lunch",
            ],
            "Lunch on Friday.",
        ),
        org_domain=ORG,
    )
    assert "E-06" in rule_ids(result)


def test_e07_link_text_mismatch() -> None:
    result = analyze_eml(
        eml(
            [
                "From: HR <hr@example.test>",
                "Authentication-Results: mx; spf=pass; dkim=pass; dmarc=pass",
                "Subject: Lunch",
            ],
            '<a href="http://evil-login.test/x">https://example.test/login</a>',
        ),
        org_domain=ORG,
    )
    assert "E-07" in rule_ids(result)


def test_e08_risky_attachment() -> None:
    raw = eml(
        [
            "From: HR <hr@example.test>",
            "Authentication-Results: mx; spf=pass; dkim=pass; dmarc=pass",
            "Subject: Invoice",
            'Content-Type: multipart/mixed; boundary="B"',
            "MIME-Version: 1.0",
        ],
        (
            "--B\nContent-Type: text/plain\n\nPlease review.\n"
            '--B\nContent-Type: application/octet-stream\n'
            'Content-Disposition: attachment; filename="Invoice.pdf.exe"\n\n'
            "data\n--B--\n"
        ),
    )
    result = analyze_eml(raw, org_domain=ORG)
    assert "E-08" in rule_ids(result)


def test_e09_content_rules_are_integrated_into_eml_analysis() -> None:
    result = analyze_eml(
        eml(
            [
                "From: Billing <billing@vendor.test>",
                "Authentication-Results: mx; spf=pass; dkim=pass; dmarc=pass",
                "Subject: Urgent invoice",
            ],
            "Please pay the invoice immediately.",
        ),
        org_domain=ORG,
    )
    assert "S-01" in rule_ids(result)
    assert "S-10" in rule_ids(result)


def test_e10_quoted_printable_body_is_decoded() -> None:
    result = analyze_eml(
        eml(
            [
                "From: HR <hr@example.test>",
                "Authentication-Results: mx; spf=pass; dkim=pass; dmarc=pass",
                "Subject: Account",
                'Content-Type: text/plain; charset="utf-8"',
                "Content-Transfer-Encoding: quoted-printable",
            ],
            "Please type your pass=77ord now.",
        ),
        org_domain=ORG,
    )
    assert "S-11" in rule_ids(result)


def test_e11_folded_headers_are_unfolded() -> None:
    result = analyze_eml(
        eml(
            [
                "From: HR <hr@example.test>",
                "Reply-To: Collector",
                " <collect@evil.test>",
                "Authentication-Results: mx; spf=pass; dkim=pass; dmarc=pass",
                "Subject: Lunch",
            ],
            "Lunch on Friday.",
        ),
        org_domain=ORG,
    )
    assert "E-05" in rule_ids(result)
    assert result.parsed["reply_to"] == "collect@evil.test"


def test_e12_total_score_and_action_advice() -> None:
    result = analyze_eml(
        eml(
            [
                "From: Billing <billing@paypa1-support.com>",
                "Reply-To: <collect@evil.test>",
                "Return-Path: <bounce@other.test>",
                "Authentication-Results: mx; spf=fail; dkim=fail; dmarc=fail",
                "Subject: Urgent verify your password",
            ],
            "Dear Customer, act now and send a gift card. Keep this confidential.",
        ),
        org_domain=ORG,
    )
    assert result.score == 100
    assert result.label == LIKELY_PHISHING
    assert len(result.what_to_do) == 4
    assert any("Report" in action for action in result.what_to_do)


def test_suspicious_band_and_advice() -> None:
    result = analyze_paste(
        sender="hr@example.test",
        subject="Invoice",
        body="Please pay the invoice immediately.",
        org_domain=ORG,
    )
    assert result.score == 35
    assert result.label == SUSPICIOUS
    assert len(result.what_to_do) == 4


def test_detection_module_does_not_import_network_clients() -> None:
    source = Path(__file__).resolve().parents[1] / "app" / "detection" / "analyzer.py"
    text = source.read_text(encoding="utf-8")
    for forbidden in ("requests", "httpx", "urllib.request", "socket", "aiohttp"):
        assert forbidden not in text
