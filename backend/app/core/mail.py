import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


def _validate_header_value(value: str, field: str) -> None:
    """Reject CR, LF or NUL to prevent SMTP/header command injection."""
    if any(char in value for char in ("\r", "\n", "\x00")):
        raise ValueError(f"{field} contains prohibited CR, LF or NUL characters")


def is_sandbox_domain(domain: str) -> bool:
    """Check if domain is in sandbox allowlist"""
    allowed = os.getenv("ALLOWED_SEND_DOMAINS", "example.com,*.test,*.invalid")
    allowed_list = [d.strip() for d in allowed.split(",")]
    
    if domain in allowed_list:
        return True
    for allowed in allowed_list:
        if allowed.startswith("*.") and domain.endswith(allowed[1:]):
            return True
    return False


def send_mail_sandbox(to_email: str, subject: str, body: str) -> bool:
    """
    Synchronous SMTP send to Mailpit with sandbox enforcement
    """
    app_env = os.getenv("APP_ENV", "development")
    if app_env == "production":
        raise ValueError("SMTP sending disabled in production")
    
    smtp_host = os.getenv("SMTP_HOST", "mailpit")
    if smtp_host != "mailpit":
        raise ValueError("SMTP host must be Mailpit in sandbox mode")
    
    _validate_header_value(to_email, "recipient")

    # Extract domain
    domain = to_email.split("@")[-1]
    if not is_sandbox_domain(domain):
        raise ValueError(f"Recipient domain {domain} not in sandbox allowlist")
    
    smtp_port = int(os.getenv("SMTP_PORT", "1025"))
    smtp_from = os.getenv("SMTP_FROM", "sandbox@example.test")
    _validate_header_value(smtp_from, "sender")

    msg = MIMEMultipart()
    msg['From'] = smtp_from
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.send_message(msg)
        return True
    except Exception as e:
        raise Exception(f"Failed to send mail: {e}")
