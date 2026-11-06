from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return config


def test_auth_migration_is_at_head(db_session: Session) -> None:
    version = db_session.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    head = ScriptDirectory.from_config(_alembic_config()).get_current_head()
    assert version == head


def test_models_and_migrations_do_not_drift(
    migrated_test_database: str, monkeypatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_test_database)
    command.check(_alembic_config())


def test_expected_auth_tables_exist(db_session: Session) -> None:
    tables = set(
        db_session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
        ).scalars()
    )
    assert {
        "organizations",
        "users",
        "sessions",
        "audit_log",
    }.issubset(tables)


def test_users_do_not_have_mfa_enabled(db_session: Session) -> None:
    columns = set(
        db_session.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'users'
                """
            )
        ).scalars()
    )
    assert "mfa_enabled" not in columns


def test_audit_log_append_only_triggers_exist(db_session: Session) -> None:
    triggers = set(
        db_session.execute(
            text(
                """
                SELECT tgname
                FROM pg_trigger
                JOIN pg_class ON pg_class.oid = pg_trigger.tgrelid
                WHERE pg_class.relname = 'audit_log'
                  AND NOT pg_trigger.tgisinternal
                """
            )
        ).scalars()
    )
    assert triggers == {
        "audit_log_no_update_delete",
        "audit_log_no_truncate",
    }


def test_org_settings_columns_exist(db_session: Session) -> None:
    columns = set(
        db_session.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'organizations'
                """
            )
        ).scalars()
    )
    assert {
        "timezone",
        "retention_days",
        "min_group_size",
        "send_domain_allowlist",
    }.issubset(columns)


def test_org_settings_check_constraints_exist(db_session: Session) -> None:
    constraints = set(
        db_session.execute(
            text(
                """
                SELECT conname
                FROM pg_constraint
                WHERE conrelid = 'organizations'::regclass
                  AND contype = 'c'
                """
            )
        ).scalars()
    )
    assert {
        "ck_organizations_retention_days",
        "ck_organizations_min_group_size",
    }.issubset(constraints)


def test_org_settings_defaults(db_session: Session) -> None:
    row = db_session.execute(
        text(
            """
            SELECT column_name, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'organizations'
              AND column_name IN ('timezone', 'retention_days', 'min_group_size')
            """
        )
    ).all()
    defaults = {name: dflt for name, dflt in row}
    assert "'UTC'" in defaults["timezone"]
    assert "90" in defaults["retention_days"]
    assert "5" in defaults["min_group_size"]
