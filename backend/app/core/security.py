import hmac
import hashlib

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=1,
    hash_len=32,
    salt_len=16,
)

DUMMY_HASH = ph.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return ph.check_needs_rehash(password_hash)
    except Exception:
        return True


def verify_password_with_dummy(password_hash: str | None, password: str) -> bool:
    if password_hash:
        try:
            return ph.verify(password_hash, password)
        except VerifyMismatchError:
            ph.verify(DUMMY_HASH, password)
            return False
    ph.verify(DUMMY_HASH, password)
    return False


def hmac_sha256(secret: str, message: str) -> bytes:
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()


def hmac_sha256_hex(secret: str, message: str) -> str:
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def compare_digest_bytes(a: bytes, b: bytes) -> bool:
    if len(a) != len(b):
        return False
    return hmac.compare_digest(a, b)
