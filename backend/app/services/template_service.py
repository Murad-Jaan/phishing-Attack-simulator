"""Template content validation, versioning and safe preview rendering.

Templates are training content. Everything stored here must stay inside the
sandbox: fictional senders on ``example.test`` / ``*.test`` / ``*.invalid``,
no real brands or domains, no credential forms and only the two supported
personalisation placeholders. The preview renderer escapes every value before
building HTML; it never trusts stored content.
"""

from __future__ import annotations

import html
import re
import uuid
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.audit import write_audit
from app.models.template import (
    Template,
    TemplateDifficulty,
    TemplateRedFlag,
    TemplateStatus,
)

ALLOWED_PLACEHOLDERS = frozenset({"first_name", "tracking_link"})
SANDBOX_DOMAINS = ("example.test", "*.test", "*.invalid")
DEMO_FIRST_NAME = "Alex"
DEMO_TRACKING_LINK = "https://tracking.example.test/c/abc123"

_EMAIL_RE = re.compile(r"([^@\s<>]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
_URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)[^\s<>\"']+")
_PLACEHOLDER_RE = re.compile(r"\{\{\s*([^{}]*?)\s*\}\}")
_TECHNIQUE_RE = re.compile(r"^(?:none|T\d{4}(?:\.\d{3})?)$")
_CREDENTIAL_PATTERNS = (
    re.compile(r"<\s*form\b", re.IGNORECASE),
    re.compile(r"<\s*input\b", re.IGNORECASE),
    re.compile(r"<\s*textarea\b", re.IGNORECASE),
    re.compile(r"<\s*select\b", re.IGNORECASE),
    re.compile(r"type\s*=\s*[\"']?password", re.IGNORECASE),
    re.compile(r"name\s*=\s*[\"']?(?:password|passwd|pwd|otp|ssn)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:enter|confirm|submit|provide|update)\s+your\s+password\b",
        re.IGNORECASE,
    ),
    re.compile(r"\benter\s+your\s+credentials\b", re.IGNORECASE),
)

# Real brands must never appear in simulation content. Lookalikes and
# misspellings used by the legacy reference are blocked too.
BRAND_TOKENS = (
    "paypal",
    "paypa1",
    "dhl",
    "fedex",
    "amazon",
    "microsoft",
    "office365",
    "outlook",
    "google",
    "gmail",
    "apple",
    "icloud",
    "facebook",
    "instagram",
    "whatsapp",
    "linkedin",
    "twitter",
    "dropbox",
    "docusign",
    "adobe",
    "netflix",
    "chase",
    "wellsfargo",
    "bankofamerica",
    "citibank",
    "hsbc",
    "coinbase",
    "steam",
)
_BRAND_RE = re.compile(
    r"(?<![a-z0-9])(?:" + "|".join(re.escape(token) for token in BRAND_TOKENS) + r")(?![a-z0-9])",
    re.IGNORECASE,
)


class TemplateValidationError(Exception):
    def __init__(self, fields: dict[str, str]):
        super().__init__("template_validation_error")
        self.fields = fields


class TemplateConflictError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def domain_is_sandbox(host: str) -> bool:
    host = host.lower().strip().rstrip(".")
    if not host:
        return False
    if host == "example.test":
        return True
    return host.endswith(".test") or host.endswith(".invalid")


def normalize_sender(sender: str) -> str:
    match = _EMAIL_RE.search(sender)
    if not match:
        raise TemplateValidationError(
            {"sender": "Sender must contain a valid email address."}
        )
    domain = match.group(2).lower().rstrip(".")
    if not domain_is_sandbox(domain):
        raise TemplateValidationError(
            {
                "sender": (
                    "Sender must use a sandbox domain: example.test, *.test or "
                    "*.invalid."
                )
            }
        )
    return sender.strip()


def _extract_link_hosts(body: str) -> list[str]:
    hosts: list[str] = []
    for raw in _URL_RE.findall(body):
        candidate = raw.rstrip(".,;:!?)]}'\"")
        if candidate.lower().startswith("www."):
            candidate = "http://" + candidate
        host = urlparse(candidate).hostname
        if host:
            hosts.append(host)
    return hosts


def _validate_placeholders(value: str, field: str, fields: dict[str, str]) -> None:
    for name in _PLACEHOLDER_RE.findall(value):
        if name not in ALLOWED_PLACEHOLDERS:
            fields[field] = (
                "Only {{first_name}} and {{tracking_link}} placeholders are allowed."
            )
            return


def _validate_no_brands(value: str, field: str, fields: dict[str, str]) -> None:
    match = _BRAND_RE.search(value)
    if match:
        fields[field] = (
            f"Real brand names are not allowed (found '{match.group(0)}'). "
            "Use fictional names instead."
        )


def validate_template_content(data: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize template content.

    ``data`` must contain every content field. Returns normalized values or
    raises :class:`TemplateValidationError` with per-field messages.
    """
    fields: dict[str, str] = {}
    normalized: dict[str, Any] = {}

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        fields["name"] = "Template name is required."
    elif len(name.strip()) > 200:
        fields["name"] = "Template name must be 200 characters or fewer."
    else:
        normalized["name"] = name.strip()
        _validate_no_brands(normalized["name"], "name", fields)

    sender = data.get("sender")
    if not isinstance(sender, str) or not sender.strip():
        fields["sender"] = "Sender is required."
    else:
        try:
            normalized["sender"] = normalize_sender(sender)
        except TemplateValidationError as exc:
            fields.update(exc.fields)
        else:
            _validate_no_brands(normalized["sender"], "sender", fields)

    subject = data.get("subject")
    if not isinstance(subject, str) or not subject.strip():
        fields["subject"] = "Subject is required."
    elif len(subject.strip()) > 300:
        fields["subject"] = "Subject must be 300 characters or fewer."
    else:
        normalized["subject"] = subject.strip()
        _validate_no_brands(normalized["subject"], "subject", fields)
        _validate_placeholders(normalized["subject"], "subject", fields)

    body = data.get("body")
    if not isinstance(body, str) or not body.strip():
        fields["body"] = "Body is required."
    else:
        normalized["body"] = body
        _validate_no_brands(body, "body", fields)
        _validate_placeholders(body, "body", fields)
        for pattern in _CREDENTIAL_PATTERNS:
            if pattern.search(body):
                fields["body"] = (
                    "Credential forms are not allowed. Simulations must never ask "
                    "for passwords or collect credentials."
                )
                break
        for host in _extract_link_hosts(body):
            if not domain_is_sandbox(host):
                fields["body"] = (
                    f"Link domain '{host}' is not allowed. Use a sandbox domain "
                    "(example.test, *.test or *.invalid)."
                )
                break

    difficulty = data.get("difficulty")
    try:
        normalized["difficulty"] = TemplateDifficulty(difficulty)
    except (TypeError, ValueError):
        fields["difficulty"] = "Difficulty must be easy, medium or hard."

    technique = data.get("attack_technique_id")
    if not isinstance(technique, str) or not technique.strip():
        fields["attack_technique_id"] = "ATT&CK technique ID is required."
    else:
        cleaned = technique.strip()
        if cleaned.lower() == "none" or cleaned.lower() == "n/a":
            cleaned = "none"
        elif cleaned.upper().startswith("T"):
            cleaned = cleaned.upper()
        if not _TECHNIQUE_RE.match(cleaned):
            fields["attack_technique_id"] = (
                "Use a MITRE ATT&CK ID such as T1566.002, or 'none' for a "
                "legitimate control."
            )
        else:
            normalized["attack_technique_id"] = cleaned

    lure_type = data.get("lure_type")
    if not isinstance(lure_type, str) or not lure_type.strip():
        fields["lure_type"] = "Lure type is required."
    elif len(lure_type.strip()) > 60:
        fields["lure_type"] = "Lure type must be 60 characters or fewer."
    else:
        normalized["lure_type"] = lure_type.strip()

    status = data.get("status", TemplateStatus.DRAFT.value)
    try:
        normalized["status"] = TemplateStatus(status)
    except (TypeError, ValueError):
        fields["status"] = "Status must be draft, published or archived."

    red_flags = data.get("red_flags", [])
    if not isinstance(red_flags, list):
        fields["red_flags"] = "Red flags must be a list."
    else:
        cleaned_flags: list[dict[str, str]] = []
        for index, flag in enumerate(red_flags):
            if not isinstance(flag, dict):
                fields["red_flags"] = "Each red flag needs a label and explanation."
                break
            label = flag.get("label")
            explanation = flag.get("explanation")
            if not isinstance(label, str) or not label.strip():
                fields[f"red_flags.{index}.label"] = "Red-flag label is required."
                break
            if not isinstance(explanation, str) or not explanation.strip():
                fields[f"red_flags.{index}.explanation"] = (
                    "Red-flag explanation is required."
                )
                break
            if len(label.strip()) > 160:
                fields[f"red_flags.{index}.label"] = (
                    "Red-flag label must be 160 characters or fewer."
                )
                break
            cleaned_flags.append(
                {"label": label.strip(), "explanation": explanation.strip()}
            )
        else:
            normalized["red_flags"] = cleaned_flags

    if fields:
        raise TemplateValidationError(fields)
    return normalized


def _audit_context(request: Any) -> dict[str, Any]:
    return {
        "request_id": getattr(getattr(request, "state", None), "request_id", None),
        "ip": getattr(getattr(request, "state", None), "client_ip", None),
        "user_agent": getattr(request, "headers", {}).get("user-agent")
        if request is not None
        else None,
    }


def _summary(template: Template) -> dict[str, Any]:
    return {
        "id": str(template.id),
        "family_id": str(template.family_id),
        "version": template.version,
        "name": template.name,
        "status": template.status.value,
        "difficulty": template.difficulty.value,
        "attack_technique_id": template.attack_technique_id,
        "lure_type": template.lure_type,
        "red_flag_count": len(template.red_flags),
    }


def _attach_red_flags(
    db: Session, template: Template, red_flags: list[dict[str, str]]
) -> None:
    for flag in red_flags:
        template.red_flags.append(
            TemplateRedFlag(label=flag["label"], explanation=flag["explanation"])
        )
    db.add(template)


def create_template(
    db: Session,
    *,
    org_id: uuid.UUID,
    actor_id: uuid.UUID,
    data: dict[str, Any],
    request: Any = None,
) -> Template:
    normalized = validate_template_content(data)
    template = Template(
        org_id=org_id,
        family_id=uuid.uuid4(),
        version=1,
        name=normalized["name"],
        sender=normalized["sender"],
        subject=normalized["subject"],
        body=normalized["body"],
        difficulty=normalized["difficulty"],
        attack_technique_id=normalized["attack_technique_id"],
        lure_type=normalized["lure_type"],
        status=normalized["status"],
        created_by=actor_id,
        updated_by=actor_id,
    )
    _attach_red_flags(db, template, normalized["red_flags"])
    db.flush()
    write_audit(
        db,
        org_id=org_id,
        actor_user_id=actor_id,
        action="template.create",
        entity_type="template",
        entity_id=str(template.id),
        after=_summary(template),
        **_audit_context(request),
    )
    return template


def _merged_data(template: Template, data: dict[str, Any]) -> dict[str, Any]:
    merged = {
        "name": template.name,
        "sender": template.sender,
        "subject": template.subject,
        "body": template.body,
        "difficulty": template.difficulty.value,
        "attack_technique_id": template.attack_technique_id,
        "lure_type": template.lure_type,
        "status": template.status.value,
        "red_flags": [
            {"label": flag.label, "explanation": flag.explanation}
            for flag in template.red_flags
        ],
    }
    merged.update({key: value for key, value in data.items() if value is not None})
    return merged


def update_template(
    db: Session,
    template: Template,
    *,
    actor_id: uuid.UUID,
    data: dict[str, Any],
    request: Any = None,
) -> Template:
    if template.status == TemplateStatus.ARCHIVED:
        raise TemplateConflictError(
            "archived_read_only",
            "Archived templates are read-only. Duplicate it to make an editable copy.",
        )

    merged = _merged_data(template, data)
    normalized = validate_template_content(merged)

    if template.status == TemplateStatus.PUBLISHED:
        max_version = db.execute(
            select(func.max(Template.version)).where(
                Template.org_id == template.org_id,
                Template.family_id == template.family_id,
            )
        ).scalar_one()
        new_template = Template(
            org_id=template.org_id,
            family_id=template.family_id,
            version=(max_version or template.version) + 1,
            name=normalized["name"],
            sender=normalized["sender"],
            subject=normalized["subject"],
            body=normalized["body"],
            difficulty=normalized["difficulty"],
            attack_technique_id=normalized["attack_technique_id"],
            lure_type=normalized["lure_type"],
            status=(
                normalized["status"]
                if data.get("status") is not None
                else TemplateStatus.DRAFT
            ),
            is_demo=template.is_demo,
            created_by=actor_id,
            updated_by=actor_id,
        )
        _attach_red_flags(db, new_template, normalized["red_flags"])
        db.flush()
        write_audit(
            db,
            org_id=template.org_id,
            actor_user_id=actor_id,
            action="template.version_create",
            entity_type="template",
            entity_id=str(new_template.id),
            before=_summary(template),
            after=_summary(new_template),
            **_audit_context(request),
        )
        return new_template

    before = _summary(template)
    template.name = normalized["name"]
    template.sender = normalized["sender"]
    template.subject = normalized["subject"]
    template.body = normalized["body"]
    template.difficulty = normalized["difficulty"]
    template.attack_technique_id = normalized["attack_technique_id"]
    template.lure_type = normalized["lure_type"]
    template.status = normalized["status"]
    template.updated_by = actor_id
    template.red_flags.clear()
    _attach_red_flags(db, template, normalized["red_flags"])
    db.flush()
    write_audit(
        db,
        org_id=template.org_id,
        actor_user_id=actor_id,
        action="template.update",
        entity_type="template",
        entity_id=str(template.id),
        before=before,
        after=_summary(template),
        **_audit_context(request),
    )
    return template


def duplicate_template(
    db: Session,
    template: Template,
    *,
    actor_id: uuid.UUID,
    name: str | None = None,
    request: Any = None,
) -> Template:
    new_name = (name or "").strip() or f"Copy of {template.name}"
    if len(new_name) > 200:
        raise TemplateValidationError(
            {"name": "Template name must be 200 characters or fewer."}
        )
    copy = Template(
        org_id=template.org_id,
        family_id=uuid.uuid4(),
        version=1,
        name=new_name,
        sender=template.sender,
        subject=template.subject,
        body=template.body,
        difficulty=template.difficulty,
        attack_technique_id=template.attack_technique_id,
        lure_type=template.lure_type,
        status=TemplateStatus.DRAFT,
        is_demo=template.is_demo,
        created_by=actor_id,
        updated_by=actor_id,
    )
    for flag in template.red_flags:
        copy.red_flags.append(
            TemplateRedFlag(label=flag.label, explanation=flag.explanation)
        )
    db.add(copy)
    db.flush()
    write_audit(
        db,
        org_id=template.org_id,
        actor_user_id=actor_id,
        action="template.duplicate",
        entity_type="template",
        entity_id=str(copy.id),
        before=_summary(template),
        after=_summary(copy),
        **_audit_context(request),
    )
    return copy


def archive_template(
    db: Session,
    template: Template,
    *,
    actor_id: uuid.UUID,
    request: Any = None,
) -> Template:
    if template.status == TemplateStatus.ARCHIVED:
        return template
    before = _summary(template)
    template.status = TemplateStatus.ARCHIVED
    template.updated_by = actor_id
    db.add(template)
    db.flush()
    write_audit(
        db,
        org_id=template.org_id,
        actor_user_id=actor_id,
        action="template.archive",
        entity_type="template",
        entity_id=str(template.id),
        before=before,
        after=_summary(template),
        **_audit_context(request),
    )
    return template


def template_payload(template: Template) -> dict[str, Any]:
    return {
        "id": str(template.id),
        "family_id": str(template.family_id),
        "version": template.version,
        "name": template.name,
        "sender": template.sender,
        "subject": template.subject,
        "body": template.body,
        "difficulty": template.difficulty.value,
        "attack_technique_id": template.attack_technique_id,
        "lure_type": template.lure_type,
        "status": template.status.value,
        "is_demo": template.is_demo,
        "red_flag_count": len(template.red_flags),
        "red_flags": [
            {
                "id": str(flag.id),
                "label": flag.label,
                "explanation": flag.explanation,
            }
            for flag in template.red_flags
        ],
        "created_at": template.created_at.isoformat()
        if template.created_at
        else None,
        "updated_at": template.updated_at.isoformat()
        if template.updated_at
        else None,
    }


def latest_templates_query(org_id: uuid.UUID):
    latest = (
        select(Template.family_id, func.max(Template.version).label("version"))
        .where(Template.org_id == org_id)
        .group_by(Template.family_id)
        .subquery()
    )
    return (
        select(Template)
        .join(
            latest,
            (Template.family_id == latest.c.family_id)
            & (Template.version == latest.c.version),
        )
        .where(Template.org_id == org_id)
        .options(selectinload(Template.red_flags))
    )


def render_preview(template: Template) -> dict[str, Any]:
    """Return an escaped HTML fragment plus the plain preview metadata.

    Every stored value is escaped. Placeholders are replaced only after
    escaping, and only with fixed sandbox demo values. No remote images,
    scripts or event handlers can survive because markup is not interpreted.
    """

    def esc(value: str) -> str:
        return html.escape(value, quote=True)

    def fill(value: str) -> str:
        escaped = esc(value)
        escaped = escaped.replace("{{first_name}}", esc(DEMO_FIRST_NAME))
        escaped = escaped.replace("{{tracking_link}}", esc(DEMO_TRACKING_LINK))
        escaped = _PLACEHOLDER_RE.sub(
            lambda match: esc(
                DEMO_FIRST_NAME
                if match.group(1) == "first_name"
                else DEMO_TRACKING_LINK
                if match.group(1) == "tracking_link"
                else ""
            ),
            escaped,
        )
        return escaped.replace("\r\n", "\n").replace("\n", "<br />")

    body_html = fill(template.body)
    sender = esc(template.sender)
    subject = fill(template.subject)
    fragment = (
        '<div class="template-preview-email" data-testid="template-preview-html">'
        '<div class="template-preview-meta">'
        f'<p class="template-preview-line"><span class="template-preview-label">From</span> {sender}</p>'
        f'<p class="template-preview-line"><span class="template-preview-label">Subject</span> {subject}</p>'
        "</div>"
        f'<div class="template-preview-body">{body_html}</div>'
        "</div>"
    )
    return {
        "html": fragment,
        "name": template.name,
        "sender": template.sender,
        "subject": template.subject,
        "difficulty": template.difficulty.value,
        "attack_technique_id": template.attack_technique_id,
        "version": template.version,
        "red_flags": [
            {
                "id": str(flag.id),
                "label": flag.label,
                "explanation": flag.explanation,
            }
            for flag in template.red_flags
        ],
    }
