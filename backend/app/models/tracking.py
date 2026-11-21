import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class TrackingEventType(str, enum.Enum):
    DELIVERED = "delivered"
    CLICKED = "clicked"
    REPORTED = "reported"
    QUIZ_COMPLETED = "quiz_completed"


class TrackingLink(Base, TimestampMixin):
    """One unguessable token per campaign/target pair."""

    __tablename__ = "tracking_links"
    __table_args__ = (
        UniqueConstraint("token", name="uq_tracking_links_token"),
        UniqueConstraint(
            "campaign_id", "target_id", name="uq_tracking_links_campaign_target"
        ),
        Index("ix_tracking_links_org_campaign", "org_id", "campaign_id"),
        Index("ix_tracking_links_target", "target_id"),
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
    token: Mapped[str] = mapped_column(String(64), nullable=False)


class TrackingEvent(Base):
    """Append-only awareness event without IP or user-agent data."""

    __tablename__ = "tracking_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('delivered', 'clicked', 'reported', 'quiz_completed')",
            name="ck_tracking_events_type",
        ),
        Index(
            "ix_tracking_events_campaign_type",
            "campaign_id",
            "event_type",
            "occurred_at",
        ),
        Index("ix_tracking_events_link_type", "tracking_link_id", "event_type"),
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
    tracking_link_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tracking_links.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tracking_link: Mapped[TrackingLink] = relationship()
