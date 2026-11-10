import enum
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class TemplateDifficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class TemplateStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


def _enum(values: type[enum.Enum], name: str) -> SAEnum:
    return SAEnum(
        values,
        name=name,
        values_callable=lambda members: [member.value for member in members],
    )


class Template(Base, TimestampMixin):
    """One immutable content version of a simulation template.

    Rows sharing ``family_id`` are versions of the same template. Editing a
    published version creates a new row; the old row is never mutated so the
    published content stays reproducible.
    """

    __tablename__ = "templates"
    __table_args__ = (
        UniqueConstraint(
            "org_id", "family_id", "version", name="uq_templates_org_family_version"
        ),
        CheckConstraint("version >= 1", name="ck_templates_version_positive"),
        Index("ix_templates_org_status", "org_id", "status"),
        Index("ix_templates_org_difficulty", "org_id", "difficulty"),
        Index("ix_templates_org_technique", "org_id", "attack_technique_id"),
        Index("ix_templates_family", "family_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), server_default=text("gen_random_uuid()"), nullable=False
    )
    version: Mapped[int] = mapped_column(
        server_default=text("1"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sender: Mapped[str] = mapped_column(String(320), nullable=False)
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[TemplateDifficulty] = mapped_column(
        _enum(TemplateDifficulty, "template_difficulty"), nullable=False
    )
    attack_technique_id: Mapped[str] = mapped_column(String(20), nullable=False)
    lure_type: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[TemplateStatus] = mapped_column(
        _enum(TemplateStatus, "template_status"),
        server_default=text("'draft'"),
        nullable=False,
    )
    is_demo: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    red_flags: Mapped[list["TemplateRedFlag"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplateRedFlag.id",
    )


class TemplateRedFlag(Base):
    __tablename__ = "template_red_flags"
    __table_args__ = (
        Index("ix_template_red_flags_template", "template_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    template: Mapped[Template] = relationship(back_populates="red_flags")
