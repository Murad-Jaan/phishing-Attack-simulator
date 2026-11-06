"""Add organization settings columns (timezone, retention, group floor, send allowlist)

Revision ID: 0003_org_settings
Revises: 0002_auth
Create Date: 2026-11-02 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003_org_settings"
down_revision = "0002_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column(
            "timezone",
            sa.String(),
            server_default=sa.text("'UTC'"),
            nullable=False,
        ),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "retention_days",
            sa.Integer(),
            server_default=sa.text("90"),
            nullable=False,
        ),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "min_group_size",
            sa.Integer(),
            server_default=sa.text("5"),
            nullable=False,
        ),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "send_domain_allowlist",
            postgresql.JSONB(),
            server_default=sa.text('\'["example.com","*.test","*.invalid"]\''),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_organizations_retention_days",
        "organizations",
        "retention_days BETWEEN 1 AND 365",
    )
    op.create_check_constraint(
        "ck_organizations_min_group_size",
        "organizations",
        "min_group_size >= 5",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_organizations_min_group_size", "organizations", type_="check"
    )
    op.drop_constraint(
        "ck_organizations_retention_days", "organizations", type_="check"
    )
    op.drop_column("organizations", "send_domain_allowlist")
    op.drop_column("organizations", "min_group_size")
    op.drop_column("organizations", "retention_days")
    op.drop_column("organizations", "timezone")
