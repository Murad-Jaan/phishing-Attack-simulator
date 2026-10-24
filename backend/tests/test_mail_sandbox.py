# Tests for SMTP sandbox enforcement
import pytest
from app.core import mail


def test_sandbox_domain_validation():
    assert mail.is_sandbox_domain("example.com") is True
    assert mail.is_sandbox_domain("test.com") is False  # not matching *.test pattern exactly
    assert mail.is_sandbox_domain("foo.test") is True  # *.test matches
    assert mail.is_sandbox_domain("bar.invalid") is True


def test_send_disabled_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(ValueError, match="disabled in production"):
        mail.send_mail_sandbox("test@example.com", "hi", "body")


def test_send_requires_mailpit_host(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    with pytest.raises(ValueError, match="must be Mailpit"):
        mail.send_mail_sandbox("test@example.com", "hi", "body")


def test_send_rejects_non_sandbox_domain(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SMTP_HOST", "mailpit")
    monkeypatch.setenv("ALLOWED_SEND_DOMAINS", "example.com,*.test,*.invalid")
    with pytest.raises(ValueError, match="not in sandbox allowlist"):
        mail.send_mail_sandbox("user@gmail.com", "hi", "body")
