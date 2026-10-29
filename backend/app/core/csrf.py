import base64
import json
import time

from fastapi import Request, Response
from starlette.datastructures import URL

from app.core.config import settings
from app.core.cookies import CSRF_COOKIE_NAME, set_csrf_cookie
from app.core.security import compare_digest_bytes, hmac_sha256


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def make_login_csrf_token() -> str:
    exp = int(time.time()) + settings.LOGIN_CSRF_TOKEN_TTL_SECONDS
    payload = json.dumps({"type": "login", "exp": exp}, separators=(",", ":")).encode()
    sig = hmac_sha256(settings.CSRF_SECRET, payload.decode())
    return f"{_b64encode(payload)}.{_b64encode(sig)}"


def make_session_csrf_token(session_id: str) -> str:
    exp = int(time.time()) + settings.CSRF_TOKEN_TTL_SECONDS
    payload = json.dumps(
        {"type": "session", "sid": session_id, "exp": exp}, separators=(",", ":")
    ).encode()
    sig = hmac_sha256(settings.CSRF_SECRET, payload.decode())
    return f"{_b64encode(payload)}.{_b64encode(sig)}"


def verify_csrf_token(token: str, session_id: str | None = None) -> bool:
    try:
        payload_b64, sig_b64 = token.split(".")
        payload = _b64decode(payload_b64)
        sig = _b64decode(sig_b64)
        expected = hmac_sha256(settings.CSRF_SECRET, payload.decode())
        if not compare_digest_bytes(sig, expected):
            return False
        data = json.loads(payload)
        if int(time.time()) > int(data["exp"]):
            return False
        if data.get("type") == "session":
            if not session_id or data.get("sid") != session_id:
                return False
            return True
        if data.get("type") == "login":
            return session_id is None
        return False
    except Exception:
        return False


def issue_login_csrf(response: Response) -> str:
    token = make_login_csrf_token()
    set_csrf_cookie(response, token)
    return token


def issue_session_csrf(response: Response, session_id: str) -> str:
    token = make_session_csrf_token(session_id)
    set_csrf_cookie(response, token)
    return token


def get_csrf_cookie(request: Request) -> str | None:
    if settings.ENV == "production" or settings.APP_ENV == "production":
        return request.cookies.get(CSRF_COOKIE_NAME) or request.cookies.get(
            "phishsim_csrf"
        )
    return request.cookies.get("phishsim_csrf") or request.cookies.get(CSRF_COOKIE_NAME)


def check_origin(request: Request) -> bool:
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    allowed = settings.APP_BASE_URL.rstrip("/")
    if origin:
        o = origin.rstrip("/")
        if o == allowed:
            return True
        return False
    if referer:
        try:
            ref = URL(referer)
            ref_base = f"{ref.scheme}://{ref.netloc}".rstrip("/")
            if ref_base == allowed:
                return True
            return False
        except Exception:
            return False
    return False
