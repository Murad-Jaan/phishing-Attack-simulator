"""Add analyzer reports storing only the verdict and rule identifiers

Revision ID: 0009_analyzer_reports
Revises: 0008_tracking_events
Create Date: 2026-11-18 23:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0009_analyzer_reports"
down_revision = "0008_tracking_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analyzer_reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("verdict", sa.String(length=32), nullable=False),
        sa.Column(
            "rule_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "verdict IN ('Safe', 'Suspicious', 'Likely phishing')",
            name="ck_analyzer_reports_verdict",
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analyzer_reports_org_created",
        "analyzer_reports",
        ["org_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_analyzer_reports_org_created", table_name="analyzer_reports")
    op.drop_table("analyzer_reports")
