# Tests for SMTP sandbox enforcement
import os

import pytest

from app.core import mail


@pytest.fixture
def sandbox_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SMTP_HOST", "mailpit")
    monkeypatch.setenv("SMTP_PORT", "1025")
    monkeypatch.setenv("SMTP_FROM", "sandbox@example.test")
    monkeypatch.setenv("ALLOWED_SEND_DOMAINS", "example.com,*.test,*.invalid")

    def fail_on_smtp(*args, **kwargs):
        raise AssertionError("SMTP must not be attempted for invalid headers")

    monkeypatch.setattr(mail.smtplib, "SMTP", fail_on_smtp)


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


@pytest.mark.parametrize("char", ["\r", "\n", "\x00"])
def test_send_rejects_recipient_control_characters(sandbox_env, char):
    with pytest.raises(ValueError, match="recipient contains prohibited"):
        mail.send_mail_sandbox(f"user@example.test{char}RCPT TO:<x@example.test>",
                               "hi", "body")


@pytest.mark.parametrize("char", ["\r", "\n"])
def test_send_rejects_sender_control_characters(sandbox_env, monkeypatch, char):
    monkeypatch.setenv(
        "SMTP_FROM", f"sandbox@example.test{char}RCPT TO:<x@example.test>"
    )
    with pytest.raises(ValueError, match="sender contains prohibited"):
        mail.send_mail_sandbox("user@example.test", "hi", "body")


def test_send_rejects_sender_nul(sandbox_env, monkeypatch):
    real_getenv = os.getenv
    injected = "sandbox@example.test\x00RCPT TO:<x@example.test>"

    def fake_getenv(key, default=None):
        if key == "SMTP_FROM":
            return injected
        return real_getenv(key, default)

    monkeypatch.setattr(mail.os, "getenv", fake_getenv)
    with pytest.raises(ValueError, match="sender contains prohibited"):
        mail.send_mail_sandbox("user@example.test", "hi", "body")
