from fastapi import Response

from app.core.config import settings


SESSION_COOKIE_NAME = "__Host-phishsim_session"
CSRF_COOKIE_NAME = "__Host-phishsim_csrf"


def _is_secure() -> bool:
    return settings.ENV == "production" or settings.APP_ENV == "production"


def set_session_cookie(response: Response, token: str) -> None:
    if _is_secure():
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=token,
            httponly=True,
            secure=True,
            samesite="lax",
            path="/",
        )
        return
    response.set_cookie(
        key="phishsim_session",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    if _is_secure():
        response.delete_cookie(
            key=SESSION_COOKIE_NAME,
            httponly=True,
            secure=True,
            samesite="lax",
            path="/",
        )
        return
    response.delete_cookie(
        key="phishsim_session",
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )


def set_csrf_cookie(response: Response, token: str) -> None:
    if _is_secure():
        response.set_cookie(
            key=CSRF_COOKIE_NAME,
            value=token,
            httponly=True,
            secure=True,
            samesite="lax",
            path="/",
        )
        return
    response.set_cookie(
        key="phishsim_csrf",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )


def clear_csrf_cookie(response: Response) -> None:
    if _is_secure():
        response.delete_cookie(
            key=CSRF_COOKIE_NAME,
            httponly=True,
            secure=True,
            samesite="lax",
            path="/",
        )
        return
    response.delete_cookie(
        key="phishsim_csrf",
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )
