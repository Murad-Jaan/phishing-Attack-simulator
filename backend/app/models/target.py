import uuid

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Target(Base, TimestampMixin):
    __tablename__ = "targets"
    __table_args__ = (
        UniqueConstraint("org_id", "email", name="uq_targets_org_email"),
        Index("ix_targets_org_active", "org_id", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
