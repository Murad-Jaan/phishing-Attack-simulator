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
    weak = security.ph.hash("x")
    # force weaker params by rehashing manually isn't easy; just verify behavior
    # create hash with current params
    strong = security.hash_password("password")
    assert security.needs_rehash(strong) is False
    # weak-like hash from different params - ph.check_needs_rehash returns True if needs rehash
    # simulate old params
    from argon2 import PasswordHasher

    old = PasswordHasher(time_cost=2, memory_cost=10240, parallelism=1)
    weak_hash = old.hash("password")
    assert security.needs_rehash(weak_hash) is True


def test_dummy_verify_called_for_unknown_user() -> None:
    with patch.object(security.ph, "verify", wraps=security.ph.verify) as mock_verify:
        result = security.verify_password_with_dummy(None, "somepassword")
        assert result is False
        # dummy verify must run
        assert mock_verify.call_count >= 1


def test_compare_digest_uses_hmac_compare_digest() -> None:
    a = b"hello"
    bbytes = b"hello"
    with patch("app.core.security.hmac.compare_digest") as mock_cd:
        mock_cd.return_value = True
        result = security.compare_digest_bytes(a, bbytes)
        assert mock_cd.called
        assert result is True
