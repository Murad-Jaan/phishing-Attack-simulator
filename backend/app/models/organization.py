import uuid

from sqlalchemy import Boolean, CheckConstraint, text
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

# Hard floor: admins may raise the reporting minimum group size but can never
# lower it below 5 (approved assumption; enforced again by the CHECK below).
MIN_GROUP_SIZE_FLOOR = 5
# Approved retention bounds: retention_days is configurable between 1 and 365
# days, default 90 (docs/assumptions.md).
RETENTION_MIN_DAYS = 1
RETENTION_MAX_DAYS = 365


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "retention_days BETWEEN 1 AND 365",
            name="ck_organizations_retention_days",
        ),
        CheckConstraint(
            "min_group_size >= 5",
            name="ck_organizations_min_group_size",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(nullable=False)
    slug: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    primary_domain: Mapped[str] = mapped_column(CITEXT, nullable=False)
    timezone: Mapped[str] = mapped_column(
        server_default=text("'UTC'"), nullable=False
    )
    retention_days: Mapped[int] = mapped_column(
        server_default=text("90"), nullable=False
    )
    min_group_size: Mapped[int] = mapped_column(
        server_default=text("5"), nullable=False
    )
    send_domain_allowlist: Mapped[list[str]] = mapped_column(
        JSONB,
        server_default=text('\'["example.com","*.test","*.invalid"]\''),
        nullable=False,
    )
    is_demo: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
