from sqlalchemy import text
from sqlalchemy.orm import Session


def test_auth_migration_is_at_head(db_session: Session) -> None:
    version = db_session.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert version == "0002_auth"


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
