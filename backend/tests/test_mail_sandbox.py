# Tests for SMTP sandbox enforcement
import os
import pytest
from app.core import mail


def test_sandbox_domain_validation():
    os.environ["ALLOWED_SEND_DOMAINS"] = "example.com,*.test,*.invalid"
    assert mail.is_sandbox_domain("example.com") == True
    assert mail.is_sandbox_domain("test.com") == False  # not matching *.test pattern exactly
    assert mail.is_sandbox_domain("foo.test") == True  # *.test matches
    assert mail.is_sandbox_domain("bar.invalid") == True


def test_send_disabled_in_production():
    os.environ["APP_ENV"] = "production"
    with pytest.raises(ValueError, match="disabled in production"):
        mail.send_mail_sandbox("test@example.com", "hi", "body")


def test_send_requires_mailpit_host():
    os.environ["APP_ENV"] = "development"
    os.environ["SMTP_HOST"] = "smtp.example.com"
    with pytest.raises(ValueError, match="must be Mailpit"):
        mail.send_mail_sandbox("test@example.com", "hi", "body")


def test_send_rejects_non_sandbox_domain():
    os.environ["APP_ENV"] = "development"
    os.environ["SMTP_HOST"] = "mailpit"
    os.environ["ALLOWED_SEND_DOMAINS"] = "example.com,*.test,*.invalid"
    with pytest.raises(ValueError, match="not in sandbox allowlist"):
        mail.send_mail_sandbox("user@gmail.com", "hi", "body")
