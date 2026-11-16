import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_AUTHORIZATION = "pending_authorization"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AuthorizationStatus(str, enum.Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    REVOKED = "revoked"


def _enum(values: type[enum.Enum], name: str) -> SAEnum:
    return SAEnum(
        values,
        name=name,
        values_callable=lambda members: [member.value for member in members],
    )


class CampaignSendStatus(str, enum.Enum):
    QUEUED = "queued"
    SENT = "sent"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Campaign(Base, TimestampMixin):
    __tablename__ = "campaigns"
    __table_args__ = (
        CheckConstraint(
            "template_version IS NULL OR template_version >= 1",
            name="ck_campaigns_template_version_positive",
        ),
        CheckConstraint(
            "rate_cap_per_hour >= 1 AND rate_cap_per_hour <= 1000",
            name="ck_campaigns_rate_cap_positive",
        ),
        CheckConstraint(
            "send_window_start IS NULL OR send_window_end IS NULL OR "
            "send_window_end > send_window_start",
            name="ck_campaigns_send_window_order",
        ),
        Index("ix_campaigns_org_updated", "org_id", "updated_at"),
        Index("ix_campaigns_org_status", "org_id", "status"),
        Index("ix_campaigns_group", "group_id"),
        Index("ix_campaigns_template", "template_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="RESTRICT"),
        nullable=True,
    )
    template_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("groups.id", ondelete="RESTRICT"),
        nullable=True,
    )
    send_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    send_window_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    send_window_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rate_cap_per_hour: Mapped[int] = mapped_column(
        Integer, server_default=text("60"), nullable=False
    )
    sending_domain: Mapped[str] = mapped_column(String(253), nullable=False)
    status: Mapped[CampaignStatus] = mapped_column(
        _enum(CampaignStatus, "campaign_status"),
        server_default=text("'draft'"),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class Authorization(Base, TimestampMixin):
    """Immutable scope approval for a campaign.

    The row captures the exact group, template version, recipient count,
    sending domain and schedule that an approver reviewed. A later campaign
    change can never silently inherit the approval: the gate compares the
    campaign against this snapshot and the approval is revoked on scope
    change.
    """

    __tablename__ = "authorizations"
    __table_args__ = (
        CheckConstraint("target_count >= 0", name="ck_authorizations_target_count"),
        CheckConstraint(
            "template_version >= 1", name="ck_authorizations_template_version_positive"
        ),
        Index("ix_authorizations_org_status", "org_id", "status"),
        Index("ix_authorizations_campaign", "campaign_id"),
        Index("ix_authorizations_requested_by", "requested_by"),
        Index("ix_authorizations_approved_by", "approved_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("groups.id", ondelete="RESTRICT"),
        nullable=False,
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="RESTRICT"),
        nullable=False,
    )
    template_version: Mapped[int] = mapped_column(Integer, nullable=False)
    target_count: Mapped[int] = mapped_column(Integer, nullable=False)
    sending_domain: Mapped[str] = mapped_column(String(253), nullable=False)
    scheduled_send_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    send_window_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    send_window_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rate_cap_per_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[AuthorizationStatus] = mapped_column(
        _enum(AuthorizationStatus, "authorization_status"),
        server_default=text("'requested'"),
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class CampaignSend(Base, TimestampMixin):
    """One idempotent delivery row per campaign/target pair."""

    __tablename__ = "campaign_sends"
    __table_args__ = (
        UniqueConstraint(
            "campaign_id", "target_id", name="uq_campaign_sends_campaign_target"
        ),
        CheckConstraint(
            "status IN ('queued', 'sent', 'skipped', 'failed', 'cancelled')",
            name="ck_campaign_sends_status",
        ),
        Index(
            "ix_campaign_sends_org_status_scheduled",
            "org_id",
            "status",
            "scheduled_for",
        ),
        Index(
            "ix_campaign_sends_campaign_status_scheduled",
            "campaign_id",
            "status",
            "scheduled_for",
        ),
        Index("ix_campaign_sends_target", "target_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("targets.id", ondelete="CASCADE"),
        nullable=False,
    )
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), server_default=text("'queued'"), nullable=False
    )
    failure_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
