import os
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.models import Organization, User, UserRole

BACKEND_DIR = Path(__file__).resolve().parent.parent
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://phish:phishpass@postgres:5432/phishsim_test",
)


def _ensure_test_database() -> None:
    url = make_url(TEST_DATABASE_URL)
    database = url.database
    if not database:
        raise RuntimeError("TEST_DATABASE_URL must include a database name")

    admin_engine = create_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    try:
        with admin_engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": database},
            ).scalar()
            if not exists:
                quoted = '"' + database.replace('"', '""') + '"'
                connection.execute(text(f"CREATE DATABASE {quoted}"))
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session")
def migrated_test_database() -> str:
    _ensure_test_database()

    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    try:
        config = Config(str(BACKEND_DIR / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        command.upgrade(config, "head")
    finally:
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url

    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
def test_engine(migrated_test_database: str) -> Generator[Engine, None, None]:
    engine = create_engine(migrated_test_database, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def organization(db_session: Session) -> Organization:
    org = Organization(
        name="Test Organization",
        slug="test-org",
        primary_domain="example.test",
        is_demo=False,
    )
    db_session.add(org)
    db_session.flush()
    return org


@pytest.fixture
def user_factory(db_session: Session, organization: Organization):
    def create_user(
        *,
        email: str = "user@example.test",
        role: UserRole = UserRole.ANALYST,
        is_active: bool = True,
        is_demo: bool = False,
    ) -> User:
        user = User(
            org_id=organization.id,
            email=email,
            password_hash="not-a-real-hash",
            display_name="Test User",
            role=role,
            is_active=is_active,
            is_demo=is_demo,
        )
        db_session.add(user)
        db_session.flush()
        return user

    return create_user


@pytest.fixture
def client_factory(db_session: Session):
    """TestClient whose app uses the SAME db session (with rollback)."""
    import app.main as app_main
    from app.db import get_db
    from fastapi.testclient import TestClient

    def _get_db_override():
        yield db_session

    app_main.app.dependency_overrides[get_db] = _get_db_override
    c = TestClient(app_main.app)
    yield c
    app_main.app.dependency_overrides.pop(get_db, None)
