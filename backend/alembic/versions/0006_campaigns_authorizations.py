"""Add campaigns and separation-of-duties authorizations

Revision ID: 0006_campaigns_authorizations
Revises: 0005_templates
Create Date: 2026-11-11 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006_campaigns_authorizations"
down_revision = "0005_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    campaign_status = postgresql.ENUM(
        "draft",
        "pending_authorization",
        "approved",
        "scheduled",
        "running",
        "paused",
        "completed",
        "cancelled",
        name="campaign_status",
        create_type=False,
    )
    authorization_status = postgresql.ENUM(
        "requested",
        "approved",
        "rejected",
        "expired",
        "revoked",
        name="authorization_status",
        create_type=False,
    )
    campaign_status.create(op.get_bind(), checkfirst=True)
    authorization_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "campaigns",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("template_version", sa.Integer(), nullable=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("send_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sending_domain", sa.String(length=253), nullable=False),
        sa.Column(
            "status",
            campaign_status,
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "template_version IS NULL OR template_version >= 1",
            name="ck_campaigns_template_version_positive",
        ),
    )
    op.create_index("ix_campaigns_org_updated", "campaigns", ["org_id", "updated_at"])
    op.create_index("ix_campaigns_org_status", "campaigns", ["org_id", "status"])
    op.create_index("ix_campaigns_group", "campaigns", ["group_id"])
    op.create_index("ix_campaigns_template", "campaigns", ["template_id"])

    op.create_table(
        "authorizations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("target_count", sa.Integer(), nullable=False),
        sa.Column("sending_domain", sa.String(length=253), nullable=False),
        sa.Column("scheduled_send_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            authorization_status,
            server_default=sa.text("'requested'"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "target_count >= 0", name="ck_authorizations_target_count"
        ),
        sa.CheckConstraint(
            "template_version >= 1",
            name="ck_authorizations_template_version_positive",
        ),
    )
    op.create_index(
        "ix_authorizations_org_status", "authorizations", ["org_id", "status"]
    )
    op.create_index(
        "ix_authorizations_campaign", "authorizations", ["campaign_id"]
    )
    op.create_index(
        "ix_authorizations_requested_by", "authorizations", ["requested_by"]
    )
    op.create_index("ix_authorizations_approved_by", "authorizations", ["approved_by"])


def downgrade() -> None:
    op.drop_index("ix_authorizations_approved_by", table_name="authorizations")
    op.drop_index("ix_authorizations_requested_by", table_name="authorizations")
    op.drop_index("ix_authorizations_campaign", table_name="authorizations")
    op.drop_index("ix_authorizations_org_status", table_name="authorizations")
    op.drop_table("authorizations")
    op.drop_index("ix_campaigns_template", table_name="campaigns")
    op.drop_index("ix_campaigns_group", table_name="campaigns")
    op.drop_index("ix_campaigns_org_status", table_name="campaigns")
    op.drop_index("ix_campaigns_org_updated", table_name="campaigns")
    op.drop_table("campaigns")
    op.execute("DROP TYPE IF EXISTS authorization_status")
    op.execute("DROP TYPE IF EXISTS campaign_status")
