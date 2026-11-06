"""Organization settings validation, updates and audit.

All settings changes go through :func:`update_organization_settings` so that
only changed fields are diffed and every real change writes one audit row
containing the before/after values of the changed fields only (no secrets —
these fields are all non-secret configuration values).
"""

from __future__ import annotations

import re
from typing import Any

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.models.organization import (
    MIN_GROUP_SIZE_FLOOR,
    RETENTION_MAX_DAYS,
    RETENTION_MIN_DAYS,
    Organization,
)

# Hard sandbox allowlist: the only sending-domain patterns ever permitted for
# simulation sending. Admins may narrow the allowlist to a subset but can
# never add anything outside this reserved set (docs/assumptions.md).
RESERVED_SEND_DOMAINS = ("example.com", "*.test", "*.invalid")

SETTING_FIELDS = (
    "name",
    "primary_domain",
    "timezone",
    "retention_days",
    "min_group_size",
    "send_domain_allowlist",
)

_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}\Z)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\Z"
)


class SettingsValidationError(Exception):
    """Validation failed; carries per-field error messages."""

    def __init__(self, fields: dict[str, str]):
        super().__init__("settings_validation_error")
        self.fields = fields


def _err(fields: dict[str, str], field: str, message: str) -> None:
    if field not in fields:
        fields[field] = message


def validate_timezone(value: str) -> str:
    name = value.strip()
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise SettingsValidationError(
            {"timezone": "Unknown timezone. Use an IANA zone name such as Europe/Berlin."}
        )
    return name


def validate_retention_days(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SettingsValidationError(
            {"retention_days": "Retention days must be a whole number of days."}
        )
    if not RETENTION_MIN_DAYS <= value <= RETENTION_MAX_DAYS:
        raise SettingsValidationError(
            {
                "retention_days": (
                    f"Retention must be between {RETENTION_MIN_DAYS} and "
                    f"{RETENTION_MAX_DAYS} days."
                )
            }
        )
    return value


def validate_min_group_size(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SettingsValidationError(
            {"min_group_size": "Minimum group size must be a whole number."}
        )
    if value < MIN_GROUP_SIZE_FLOOR:
        raise SettingsValidationError(
            {
                "min_group_size": (
                    "Minimum group size has a hard floor of 5. You can raise it, "
                    "but never lower it below 5."
                )
            }
        )
    return value


def validate_send_domain_allowlist(value: Any) -> list[str]:
    def fail(message: str) -> None:
        raise SettingsValidationError({"send_domain_allowlist": message})

    if not isinstance(value, list) or any(
        not isinstance(item, str) for item in value
    ):
        fail("Sending domains must be a list of domain patterns.")
    normalized: list[str] = []
    for raw in value:
        entry = raw.strip().lower()
        if not entry:
            fail("Empty domain entries are not allowed.")
        if entry not in RESERVED_SEND_DOMAINS:
            fail(
                "Only the reserved sandbox domains example.com, *.test and "
                "*.invalid are allowed."
            )
        if entry in normalized:
            fail(f"Duplicate entry: {entry}.")
        normalized.append(entry)
    if not normalized:
        fail(
            "The sending-domain allowlist cannot be empty. Keep at least one "
            "reserved sandbox domain."
        )
    return normalized


def validate_settings(data: dict[str, Any]) -> dict[str, Any]:
    """Validate provided settings keys and return their normalized values.

    Raises :class:`SettingsValidationError` collecting one message per bad
    field. Only keys present in ``data`` are validated and returned.
    """
    fields: dict[str, str] = {}
    normalized: dict[str, Any] = {}

    if "name" in data:
        name = data["name"]
        if not isinstance(name, str) or not name.strip():
            _err(fields, "name", "Organization name is required.")
        elif len(name.strip()) > 200:
            _err(fields, "name", "Organization name must be 200 characters or fewer.")
        else:
            normalized["name"] = name.strip()

    if "primary_domain" in data:
        domain = data["primary_domain"]
        if isinstance(domain, str):
            domain = domain.strip().lower()
        if not isinstance(domain, str) or not domain or not _DOMAIN_RE.match(domain):
            _err(
                fields,
                "primary_domain",
                "Enter a valid domain name such as acme.test (no scheme, no path).",
            )
        else:
            normalized["primary_domain"] = domain

    if "timezone" in data:
        value = data["timezone"]
        if not isinstance(value, str):
            _err(fields, "timezone", "Timezone must be an IANA zone name.")
        else:
            try:
                normalized["timezone"] = validate_timezone(value)
            except SettingsValidationError as exc:
                fields.update(exc.fields)

    if "retention_days" in data:
        try:
            normalized["retention_days"] = validate_retention_days(
                data["retention_days"]
            )
        except SettingsValidationError as exc:
            fields.update(exc.fields)

    if "min_group_size" in data:
        try:
            normalized["min_group_size"] = validate_min_group_size(
                data["min_group_size"]
            )
        except SettingsValidationError as exc:
            fields.update(exc.fields)

    if "send_domain_allowlist" in data:
        try:
            normalized["send_domain_allowlist"] = validate_send_domain_allowlist(
                data["send_domain_allowlist"]
            )
        except SettingsValidationError as exc:
            fields.update(exc.fields)

    if fields:
        raise SettingsValidationError(fields)
    return normalized


def update_organization_settings(
    db: Session,
    org: Organization,
    normalized: dict[str, Any],
    *,
    actor_user_id,
    request_id: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> bool:
    """Apply normalized changes and audit the change.

    Only changed fields appear in the audit before/after payloads. A no-op
    (no field actually changed) writes no audit row. Returns True when a
    change was applied.
    """
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    for field, value in normalized.items():
        current = getattr(org, field)
        if current != value:
            before[field] = current
            after[field] = value
            setattr(org, field, value)
    if not before:
        return False
    db.add(org)
    db.flush()
    write_audit(
        db,
        org_id=org.id,
        actor_user_id=actor_user_id,
        action="org_settings.update",
        entity_type="organization",
        entity_id=str(org.id),
        before=before,
        after=after,
        request_id=request_id,
        ip=ip,
        user_agent=user_agent,
    )
    return True


def settings_payload(org: Organization) -> dict[str, Any]:
    """Serialize the current settings for the GET endpoint."""
    return {
        "name": org.name,
        "primary_domain": org.primary_domain,
        "timezone": org.timezone,
        "retention_days": org.retention_days,
        "min_group_size": org.min_group_size,
        "send_domain_allowlist": list(org.send_domain_allowlist),
    }
