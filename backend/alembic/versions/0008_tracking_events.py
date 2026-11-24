"""Add per-target tracking links and append-only tracking events

Revision ID: 0008_tracking_events
Revises: 0007_campaign_scheduling
Create Date: 2026-11-18 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0008_tracking_events"
down_revision = "0007_campaign_scheduling"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "campaigns",
        sa.Column("tracking_base_url", sa.String(length=300), nullable=True),
    )

    op.create_table(
        "tracking_links",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["campaigns.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token", name="uq_tracking_links_token"),
        sa.UniqueConstraint(
            "campaign_id", "target_id", name="uq_tracking_links_campaign_target"
        ),
    )
    op.create_index(
        "ix_tracking_links_org_campaign", "tracking_links", ["org_id", "campaign_id"]
    )
    op.create_index("ix_tracking_links_target", "tracking_links", ["target_id"])

    op.create_table(
        "tracking_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tracking_link_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ('delivered', 'clicked', 'reported', 'quiz_completed')",
            name="ck_tracking_events_type",
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["campaigns.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["tracking_link_id"], ["tracking_links.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tracking_events_campaign_type",
        "tracking_events",
        ["campaign_id", "event_type", "occurred_at"],
    )
    op.create_index(
        "ix_tracking_events_link_type",
        "tracking_events",
        ["tracking_link_id", "event_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_tracking_events_link_type", table_name="tracking_events")
    op.drop_index("ix_tracking_events_campaign_type", table_name="tracking_events")
    op.drop_table("tracking_events")

    op.drop_index("ix_tracking_links_target", table_name="tracking_links")
    op.drop_index("ix_tracking_links_org_campaign", table_name="tracking_links")
    op.drop_table("tracking_links")

    op.drop_column("campaigns", "tracking_base_url")
