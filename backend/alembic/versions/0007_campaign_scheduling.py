"""Add campaign scheduling, send window, rate caps and send journal

Revision ID: 0007_campaign_scheduling
Revises: 0006_campaigns_authorizations
Create Date: 2026-11-16 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0007_campaign_scheduling"
down_revision = "0006_campaigns_authorizations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "campaigns",
        sa.Column("send_window_start", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "campaigns",
        sa.Column("send_window_end", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "rate_cap_per_hour",
            sa.Integer(),
            server_default=sa.text("60"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_campaigns_rate_cap_positive",
        "campaigns",
        "rate_cap_per_hour >= 1 AND rate_cap_per_hour <= 1000",
    )
    op.create_check_constraint(
        "ck_campaigns_send_window_order",
        "campaigns",
        "send_window_start IS NULL OR send_window_end IS NULL OR "
        "send_window_end > send_window_start",
    )

    op.add_column(
        "authorizations",
        sa.Column("send_window_start", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "authorizations",
        sa.Column("send_window_end", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "authorizations",
        sa.Column("rate_cap_per_hour", sa.Integer(), nullable=True),
    )

    op.create_table(
        "campaign_sends",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'queued'"), nullable=False),
        sa.Column("failure_code", sa.String(length=50), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('queued', 'sent', 'skipped', 'failed', 'cancelled')",
            name="ck_campaign_sends_status",
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["campaigns.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id", "target_id", name="uq_campaign_sends_campaign_target"
        ),
    )
    op.create_index(
        "ix_campaign_sends_org_status_scheduled",
        "campaign_sends",
        ["org_id", "status", "scheduled_for"],
    )
    op.create_index(
        "ix_campaign_sends_campaign_status_scheduled",
        "campaign_sends",
        ["campaign_id", "status", "scheduled_for"],
    )
    op.create_index(
        "ix_campaign_sends_target", "campaign_sends", ["target_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_campaign_sends_target", table_name="campaign_sends")
    op.drop_index(
        "ix_campaign_sends_campaign_status_scheduled", table_name="campaign_sends"
    )
    op.drop_index(
        "ix_campaign_sends_org_status_scheduled", table_name="campaign_sends"
    )
    op.drop_table("campaign_sends")

    op.drop_column("authorizations", "rate_cap_per_hour")
    op.drop_column("authorizations", "send_window_end")
    op.drop_column("authorizations", "send_window_start")

    op.drop_constraint(
        "ck_campaigns_send_window_order", "campaigns", type_="check"
    )
    op.drop_constraint(
        "ck_campaigns_rate_cap_positive", "campaigns", type_="check"
    )
    op.drop_column("campaigns", "rate_cap_per_hour")
    op.drop_column("campaigns", "send_window_end")
    op.drop_column("campaigns", "send_window_start")
