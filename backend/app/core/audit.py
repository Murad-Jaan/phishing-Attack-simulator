from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


REDACT_KEYS = {
    "password",
    "password_hash",
    "token",
    "session_token",
    "csrf",
    "csrf_token",
    "secret",
    "authorization",
    "cookie",
}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            kl = k.lower()
            if kl in REDACT_KEYS:
                continue
            if "token" in kl or "hash" in kl or "csrf" in kl or "cookie" in kl or "auth" in kl:
                continue
            out[k] = _redact(v)
        return out
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def _hash_bytes(value: str | None) -> bytes | None:
    if value is None or value == "":
        return None
    import hashlib

    return hashlib.sha256(value.encode()).digest()


def write_audit(
    db: Session,
    *,
    org_id,
    actor_user_id,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
    ip_hash: bytes | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> AuditLog:
    if ip_hash is None and ip:
        ip_hash = _hash_bytes(ip)
    if user_agent:
        ua_hash = _hash_bytes(user_agent)
        if ua_hash and reason is None:
            reason = f"ua:{ua_hash.hex()}"
    row = AuditLog(
        org_id=org_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=_redact(before) if before is not None else None,
        after=_redact(after) if after is not None else None,
        reason=reason,
        ip_hash=ip_hash,
        request_id=request_id,
    )
    db.add(row)
    db.flush()
    return row
