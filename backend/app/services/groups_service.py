"""Groups, targets and CSV import helpers.

CSV import is intentionally strict: the file is parsed in memory, never
written to disk, validated row by row and imported partially so that valid
rows are kept when some rows fail. Formula-injection prefixes are rejected
rather than neutralised, and the import audit row contains counts only.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.group import Group, GroupMember
from app.models.organization import Organization
from app.models.target import Target

CSV_MAX_BYTES = 5 * 1024 * 1024
FORMULA_PREFIXES = ("=", "+", "-", "@")
_HEADER_EMAIL = "email"
_HEADER_DISPLAY_NAMES = ("display_name", "name")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CsvFileError(Exception):
    """File-level CSV problem (header, encoding, empty file)."""


def normalize_email(raw: str) -> str:
    value = raw.strip()
    if not _EMAIL_RE.match(value):
        raise ValueError("invalid email")
    try:
        result = validate_email(
            value, check_deliverability=False, test_environment=True
        )
    except EmailNotValidError as exc:
        raise ValueError("invalid email") from exc
    return result.normalized.lower()


def is_formula_cell(value: str) -> bool:
    return value.lstrip().startswith(FORMULA_PREFIXES)


@dataclass(frozen=True)
class ParsedTarget:
    row: int
    email: str
    display_name: str | None


@dataclass(frozen=True)
class RowError:
    row: int
    message: str

    def as_dict(self) -> dict[str, object]:
        return {"row": self.row, "message": self.message, "line": f"Row {self.row}: {self.message}"}


def parse_csv(data: bytes) -> tuple[list[ParsedTarget], list[RowError], int]:
    """Parse and validate an uploaded CSV.

    Returns (valid rows, row errors, total data rows). Raises CsvFileError
    for problems that make the whole file unusable.
    """
    if not data:
        raise CsvFileError("The CSV file is empty.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvFileError("The CSV file must be UTF-8 encoded.") from exc

    try:
        rows = list(csv.reader(io.StringIO(text, newline="")))
    except csv.Error as exc:
        raise CsvFileError("The CSV file could not be parsed.") from exc

    rows = [r for r in rows if any(cell.strip() for cell in r)]
    if not rows:
        raise CsvFileError("The CSV file is empty.")

    header = [cell.strip().lower() for cell in rows[0]]
    if _HEADER_EMAIL not in header:
        raise CsvFileError("The CSV must include an email column.")

    email_idx = header.index(_HEADER_EMAIL)
    display_idx: int | None = None
    for candidate in _HEADER_DISPLAY_NAMES:
        if candidate in header:
            display_idx = header.index(candidate)
            break

    parsed: list[ParsedTarget] = []
    errors: list[RowError] = []
    seen: set[str] = set()
    data_rows = rows[1:]

    for offset, row in enumerate(data_rows, start=2):
        cells = [cell.strip() for cell in row]
        email_raw = cells[email_idx] if email_idx < len(cells) else ""
        display_raw = (
            cells[display_idx]
            if display_idx is not None and display_idx < len(cells)
            else ""
        )

        if not email_raw and not display_raw:
            continue

        if is_formula_cell(email_raw):
            errors.append(RowError(offset, "formula injection blocked"))
            continue
        if is_formula_cell(display_raw):
            errors.append(RowError(offset, "formula injection blocked"))
            continue

        if not email_raw:
            errors.append(RowError(offset, "email is required"))
            continue

        try:
            email = normalize_email(email_raw)
        except ValueError:
            errors.append(RowError(offset, "invalid email"))
            continue

        if email in seen:
            errors.append(RowError(offset, "duplicate email"))
            continue
        seen.add(email)

        parsed.append(
            ParsedTarget(
                row=offset,
                email=email,
                display_name=display_raw or None,
            )
        )

    return parsed, errors, len(data_rows)


def member_count(db: Session, group_id) -> int:
    return int(
        db.execute(
            select(func.count(GroupMember.id)).where(
                GroupMember.group_id == group_id
            )
        ).scalar_one()
    )


def group_members(db: Session, group_id) -> list[Target]:
    return list(
        db.execute(
            select(Target)
            .join(GroupMember, GroupMember.target_id == Target.id)
            .where(GroupMember.group_id == group_id)
            .order_by(Target.email)
        ).scalars()
    )


def serialize_target(target: Target) -> dict[str, object]:
    return {
        "id": str(target.id),
        "email": target.email,
        "display_name": target.display_name,
        "org_id": str(target.org_id),
    }


def serialize_group(
    db: Session, group: Group, min_group_size: int, *, include_members: bool = False
) -> dict[str, object]:
    count = member_count(db, group.id)
    payload: dict[str, object] = {
        "id": str(group.id),
        "org_id": str(group.org_id),
        "name": group.name,
        "description": group.description,
        "department": group.department,
        "member_count": count,
        "min_group_size": min_group_size,
        "suppressed": count < min_group_size,
        "created_at": group.created_at.isoformat() if group.created_at else None,
        "updated_at": group.updated_at.isoformat() if group.updated_at else None,
    }
    if include_members:
        payload["members"] = [serialize_target(t) for t in group_members(db, group.id)]
    return payload


def import_targets(
    db: Session,
    org: Organization,
    group: Group,
    data: bytes,
) -> dict[str, object]:
    """Partially import valid CSV rows into an existing group.

    The caller owns the transaction and the audit entry. No raw file content
    or email address is returned in the import summary.
    """
    parsed, errors, total = parse_csv(data)
    imported = 0

    for item in parsed:
        target = db.execute(
            select(Target).where(Target.org_id == org.id, Target.email == item.email)
        ).scalar_one_or_none()
        if target is None:
            target = Target(
                org_id=org.id,
                email=item.email,
                display_name=item.display_name,
            )
            db.add(target)
            db.flush()
        elif item.display_name and not target.display_name:
            target.display_name = item.display_name
            db.add(target)
            db.flush()

        exists = db.execute(
            select(GroupMember.id).where(
                GroupMember.group_id == group.id,
                GroupMember.target_id == target.id,
            )
        ).scalar_one_or_none()
        if exists is not None:
            errors.append(RowError(item.row, "duplicate email"))
            continue

        db.add(GroupMember(group_id=group.id, target_id=target.id))
        db.flush()
        imported += 1

    errors.sort(key=lambda e: e.row)
    error_dicts = [e.as_dict() for e in errors]
    return {
        "imported": imported,
        "skipped": len(error_dicts),
        "total": total,
        "errors": error_dicts,
    }
