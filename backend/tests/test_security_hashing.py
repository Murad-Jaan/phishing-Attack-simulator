from unittest.mock import patch

from app.core import security


def test_argon2id_hash_format_and_verify() -> None:
    password = "TestPassword123!"
    hashed = security.hash_password(password)
    assert hashed.startswith("$argon2id$")
    assert "m=65536" in hashed
    assert "t=3" in hashed
    assert "p=1" in hashed
    assert security.verify_password(hashed, password) is True
    assert security.verify_password(hashed, "WrongPassword!") is False


def test_needs_rehash() -> None:
    strong = security.hash_password("password")
    assert security.needs_rehash(strong) is False
    from argon2 import PasswordHasher
    old = PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)
    weak_hash = old.hash("password")
    assert security.needs_rehash(weak_hash) is True


def test_dummy_verify_called_for_unknown_user() -> None:
    with patch("app.core.security.ph") as mock_ph:
        mock_ph.verify.return_value = False
        result = security.verify_password_with_dummy(None, "somepassword")
        assert result is False
        assert mock_ph.verify.called


def test_compare_digest_uses_hmac_compare_digest() -> None:
    a = b"hello"
    bbytes = b"hello"
    with patch("app.core.security.hmac.compare_digest") as mock_cd:
        mock_cd.return_value = True
        result = security.compare_digest_bytes(a, bbytes)
        assert mock_cd.called
        assert result is True
