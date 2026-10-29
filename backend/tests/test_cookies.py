from fastapi import Response

from app.core import cookies


def test_cookies_production_flags() -> None:
    import os

    old_env = os.environ.get("ENV")
    old_app = os.environ.get("APP_ENV")
    os.environ["ENV"] = "production"
    os.environ["APP_ENV"] = "production"
    try:
        from app.core import config

        config.settings.ENV = "production"
        config.settings.APP_ENV = "production"
        resp = Response()
        cookies.set_session_cookie(resp, "token123")
        cookies.set_csrf_cookie(resp, "csrf123")
        session_cookie = None
        csrf_cookie = None
        for c in resp.raw_headers:
            if c[0].lower() == b"set-cookie":
                val = c[1].decode()
                if cookies.SESSION_COOKIE_NAME in val:
                    session_cookie = val
                if cookies.CSRF_COOKIE_NAME in val:
                    csrf_cookie = val
        assert session_cookie is not None
        assert csrf_cookie is not None
        assert cookies.SESSION_COOKIE_NAME == "__Host-phishsim_session"
        assert cookies.CSRF_COOKIE_NAME == "__Host-phishsim_csrf"
        assert "httponly" in session_cookie.lower()
        assert "secure" in session_cookie.lower()
        assert "samesite=lax" in session_cookie.lower()
        assert "path=/" in session_cookie.lower()
        assert "domain=" not in session_cookie.lower()
        assert "max-age" not in session_cookie.lower()
    finally:
        if old_env is None:
            os.environ.pop("ENV", None)
        else:
            os.environ["ENV"] = old_env
        if old_app is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = old_app


def test_cookies_development_flags() -> None:
    import os

    old_env = os.environ.get("ENV")
    old_app = os.environ.get("APP_ENV")
    os.environ["ENV"] = "development"
    os.environ["APP_ENV"] = "development"
    try:
        from app.core import config

        config.settings.ENV = "development"
        config.settings.APP_ENV = "development"
        resp = Response()
        cookies.set_session_cookie(resp, "token123")
        cookies.set_csrf_cookie(resp, "csrf123")
        session_cookie = None
        csrf_cookie = None
        for c in resp.raw_headers:
            if c[0].lower() == b"set-cookie":
                val = c[1].decode()
                if "phishsim_session" in val and "__Host" not in val:
                    session_cookie = val
                if "phishsim_csrf" in val and "__Host" not in val:
                    csrf_cookie = val
        assert session_cookie is not None
        assert csrf_cookie is not None
        assert "httponly" in session_cookie.lower()
        assert "secure" not in session_cookie.lower()
        assert "samesite=lax" in session_cookie.lower()
    finally:
        if old_env is None:
            os.environ.pop("ENV", None)
        else:
            os.environ["ENV"] = old_env
        if old_app is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = old_app


def test_clear_cookie_sets_expired() -> None:
    import os

    old_env = os.environ.get("ENV")
    old_app = os.environ.get("APP_ENV")
    os.environ["ENV"] = "development"
    os.environ["APP_ENV"] = "development"
    try:
        resp = Response()
        cookies.clear_session_cookie(resp)
        cookie = None
        for c in resp.raw_headers:
            if c[0].lower() == b"set-cookie":
                val = c[1].decode()
                if "phishsim_session" in val:
                    cookie = val
                    break
        assert cookie is not None
        assert "phishsim_session" in cookie
        assert "path=/" in cookie.lower()
    finally:
        if old_env is None:
            os.environ.pop("ENV", None)
        else:
            os.environ["ENV"] = old_env
        if old_app is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = old_app
