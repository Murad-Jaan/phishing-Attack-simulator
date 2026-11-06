"""M2 minimum group size: hard floor of 5 (raise yes, lower no)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.models.user import UserRole
from tests.conftest import login_as, session_csrf_token

SETTINGS_URL = "/api/v1/settings/organization"


def _login_admin(db_session, client_factory, user_factory, email: str) -> str:
    user = user_factory(email=email, role=UserRole.ADMIN)
    user.password_hash = hash_password("pass123456")
    db_session.commit()
    login_as(client_factory, email, "pass123456")
    return session_csrf_token(client_factory)


def test_raise_from_5_to_10_ok(db_session, client_factory, user_factory):
    token = _login_admin(db_session, client_factory, user_factory, "floor-raise@example.test")
    r = client_factory.patch(
        SETTINGS_URL, json={"min_group_size": 10}, headers={"X-CSRF-Token": token}
    )
    assert r.status_code == 200, r.text
    assert r.json()["settings"]["min_group_size"] == 10


def test_raise_to_large_value_ok(db_session, client_factory, user_factory):
    token = _login_admin(db_session, client_factory, user_factory, "floor-large@example.test")
    r = client_factory.patch(
        SETTINGS_URL, json={"min_group_size": 500}, headers={"X-CSRF-Token": token}
    )
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("lower", [3, 4, 0, -5])
def test_lower_below_floor_rejected(db_session, client_factory, user_factory, lower):
    token = _login_admin(db_session, client_factory, user_factory, f"floor-lower-{lower}@example.test")
    r = client_factory.patch(
        SETTINGS_URL, json={"min_group_size": lower}, headers={"X-CSRF-Token": token}
    )
    assert r.status_code == 422
    fields = r.json()["error"]["fields"]
    assert "min_group_size" in fields
    assert "5" in fields["min_group_size"]


def test_lower_back_to_floor_ok(db_session, client_factory, user_factory):
    """10 -> 5 is fine; the floor itself is always allowed."""
    token = _login_admin(db_session, client_factory, user_factory, "floor-back@example.test")
    r1 = client_factory.patch(
        SETTINGS_URL, json={"min_group_size": 10}, headers={"X-CSRF-Token": token}
    )
    assert r1.status_code == 200, r1.text
    r2 = client_factory.patch(
        SETTINGS_URL, json={"min_group_size": 5}, headers={"X-CSRF-Token": token}
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["settings"]["min_group_size"] == 5


def test_lowering_unchanged_value_is_noop(db_session, client_factory, user_factory):
    token = _login_admin(db_session, client_factory, user_factory, "floor-noop@example.test")
    r = client_factory.patch(
        SETTINGS_URL, json={"min_group_size": 5}, headers={"X-CSRF-Token": token}
    )
    assert r.status_code == 200, r.text


def test_db_check_rejects_min_group_size_below_floor(db_session, organization):
    """Direct SQL below the floor must be rejected by the CHECK constraint."""
    db_session.commit()
    with pytest.raises(IntegrityError):
        db_session.execute(
            text("UPDATE organizations SET min_group_size = 4 WHERE id = :id"),
            {"id": organization.id},
        )
    db_session.rollback()
    with pytest.raises(IntegrityError):
        db_session.execute(
            text("UPDATE organizations SET min_group_size = 0 WHERE id = :id"),
            {"id": organization.id},
        )
    db_session.rollback()
    db_session.execute(
        text("UPDATE organizations SET min_group_size = 5 WHERE id = :id"),
        {"id": organization.id},
    )
