from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.rate_limit import RateLimitResult
from app.core.security import hash_password
from app.models import AnalyzerReport, UserRole
from tests.conftest import login_as, session_csrf_token


def _login(db_session, client, user_factory, *, email: str = "analyst@example.test"):
    user = user_factory(email=email, role=UserRole.ANALYST)
    user.password_hash = hash_password("pass123456")
    db_session.commit()
    login_as(client, email, "pass123456")
    return user


def _csrf(client) -> dict[str, str]:
    return {"X-CSRF-Token": session_csrf_token(client)}


PASTE = {
    "sender": "security@paypa1-support.com",
    "subject": "URGENT: verify your password",
    "body": "Dear Customer, act now and confirm your password.",
    "link": "http://paypa1-verify.com/login",
    "consent": True,
}


def test_analyzer_requires_authentication(client_factory) -> None:
    r = client_factory.post("/api/v1/analyzer", json=PASTE)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"


def test_analyzer_requires_csrf(db_session, client_factory, user_factory) -> None:
    _login(db_session, client_factory, user_factory)
    r = client_factory.post("/api/v1/analyzer", json=PASTE)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "csrf_failed"


def test_analyzer_paste_returns_reasons_without_echoing_content(
    db_session, client_factory, user_factory
) -> None:
    _login(db_session, client_factory, user_factory)
    body = "Dear Customer, act now and confirm your password."
    r = client_factory.post(
        "/api/v1/analyzer",
        json={**PASTE, "body": body},
        headers=_csrf(client_factory),
    )
    assert r.status_code == 200, r.text
    analysis = r.json()["analysis"]
    assert analysis["label"] == "Likely phishing"
    assert analysis["score"] >= 60
    assert "S-03" in analysis["rule_ids"]
    assert "S-11" in analysis["rule_ids"]
    assert analysis["what_to_do"]
    assert body not in r.text
    assert analysis["parsed"]["from"] == "security@paypa1-support.com"


def test_analyzer_requires_consent(db_session, client_factory, user_factory) -> None:
    _login(db_session, client_factory, user_factory)
    payload = {key: value for key, value in PASTE.items() if key != "consent"}
    r = client_factory.post(
        "/api/v1/analyzer", json=payload, headers=_csrf(client_factory)
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
    assert "consent" in r.json()["error"]["fields"]


def test_analyzer_rejects_oversized_upload(
    db_session, client_factory, user_factory
) -> None:
    _login(db_session, client_factory, user_factory)
    r = client_factory.post(
        "/api/v1/analyzer",
        data={"consent": "true"},
        files={"file": ("big.eml", b"a" * 5_000_001, "message/rfc822")},
        headers=_csrf(client_factory),
    )
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "file_too_large"


def test_analyzer_accepts_eml_upload(db_session, client_factory, user_factory) -> None:
    _login(db_session, client_factory, user_factory)
    raw = (
        'From: "PayPal" <service@paypa1-support.com>\n'
        "Reply-To: <collect@evil.test>\n"
        "Authentication-Results: mx; spf=fail; dkim=fail; dmarc=fail\n"
        "Subject: Urgent verify your password\n\n"
        '<a href="http://evil-login.test/x">https://paypal.com/login</a>\n'
    )
    r = client_factory.post(
        "/api/v1/analyzer",
        data={"consent": "true"},
        files={"file": ("message.eml", raw.encode(), "message/rfc822")},
        headers=_csrf(client_factory),
    )
    assert r.status_code == 200, r.text
    analysis = r.json()["analysis"]
    for expected in ("E-02", "E-03", "E-04", "E-05", "E-07"):
        assert expected in analysis["rule_ids"]
    assert analysis["parsed"]["reply_to"] == "collect@evil.test"


def test_analyzer_report_persists_verdict_and_rule_ids_only(
    db_session, client_factory, user_factory
) -> None:
    user = _login(db_session, client_factory, user_factory)
    r = client_factory.post(
        "/api/v1/analyzer/report",
        json={"label": "Likely phishing", "rule_ids": ["S-03", "S-11", "S-03"]},
        headers=_csrf(client_factory),
    )
    assert r.status_code == 201, r.text
    assert r.json()["ok"] is True

    row = db_session.execute(
        select(AnalyzerReport).where(AnalyzerReport.user_id == user.id)
    ).scalar_one()
    assert row.org_id == user.org_id
    assert row.verdict == "Likely phishing"
    assert row.rule_ids == ["S-03", "S-11"]
    assert not hasattr(row, "body")
    assert not hasattr(row, "sender")


def test_analyzer_report_rejects_unknown_verdict(
    db_session, client_factory, user_factory
) -> None:
    _login(db_session, client_factory, user_factory)
    r = client_factory.post(
        "/api/v1/analyzer/report",
        json={"label": "Totally fine", "rule_ids": []},
        headers=_csrf(client_factory),
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_error"


def test_analyzer_rate_limit_returns_429(
    db_session, client_factory, user_factory, monkeypatch
) -> None:
    _login(db_session, client_factory, user_factory)

    def _denied(*_args, **_kwargs):
        return RateLimitResult(False, 42)

    monkeypatch.setattr(
        "app.api.v1.analyzer.rate_limit.check_analyzer_rate_limit", _denied
    )
    r = client_factory.post(
        "/api/v1/analyzer", json=PASTE, headers=_csrf(client_factory)
    )
    assert r.status_code == 429
    assert r.headers["Retry-After"] == "42"
    assert r.json()["error"]["code"] == "rate_limited"


@pytest.mark.parametrize(
    "url",
    ["/api/v1/analyzer", "/api/v1/analyzer/report"],
)
def test_analyzer_json_rejects_unknown_fields(
    db_session, client_factory, user_factory, url: str
) -> None:
    _login(db_session, client_factory, user_factory)
    r = client_factory.post(
        url,
        json={"unexpected": "value", "consent": True, "label": "Safe"},
        headers=_csrf(client_factory),
    )
    assert r.status_code == (400 if url == "/api/v1/analyzer/report" else 422)
