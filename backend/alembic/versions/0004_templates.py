"""Add versioned simulation templates and red-flag metadata

Revision ID: 0004_templates
Revises: 0003_org_settings
Create Date: 2026-11-10 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004_templates"
down_revision = "0003_org_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    template_difficulty = postgresql.ENUM(
        "easy", "medium", "hard", name="template_difficulty", create_type=False
    )
    template_status = postgresql.ENUM(
        "draft", "published", "archived", name="template_status", create_type=False
    )
    template_difficulty.create(op.get_bind(), checkfirst=True)
    template_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "templates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "family_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("sender", sa.String(length=320), nullable=False),
        sa.Column("subject", sa.String(length=300), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("difficulty", template_difficulty, nullable=False),
        sa.Column("attack_technique_id", sa.String(length=20), nullable=False),
        sa.Column("lure_type", sa.String(length=60), nullable=False),
        sa.Column(
            "status",
            template_status,
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column(
            "is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id", "family_id", "version", name="uq_templates_org_family_version"
        ),
        sa.CheckConstraint("version >= 1", name="ck_templates_version_positive"),
    )
    op.create_index("ix_templates_org_status", "templates", ["org_id", "status"])
    op.create_index(
        "ix_templates_org_difficulty", "templates", ["org_id", "difficulty"]
    )
    op.create_index(
        "ix_templates_org_technique", "templates", ["org_id", "attack_technique_id"]
    )
    op.create_index("ix_templates_family", "templates", ["family_id"])

    op.create_table(
        "template_red_flags",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_template_red_flags_template", "template_red_flags", ["template_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_template_red_flags_template", table_name="template_red_flags"
    )
    op.drop_table("template_red_flags")
    op.drop_index("ix_templates_family", table_name="templates")
    op.drop_index("ix_templates_org_technique", table_name="templates")
    op.drop_index("ix_templates_org_difficulty", table_name="templates")
    op.drop_index("ix_templates_org_status", table_name="templates")
    op.drop_table("templates")
    op.execute("DROP TYPE IF EXISTS template_status")
    op.execute("DROP TYPE IF EXISTS template_difficulty")
