import os

from app.core import config


def test_production_refuses_changeme() -> None:
    old_env = os.environ.get("ENV")
    old_app = os.environ.get("APP_ENV")
    old_session = os.environ.get("SESSION_SECRET")
    old_csrf = os.environ.get("CSRF_SECRET")
    try:
        os.environ["ENV"] = "production"
        os.environ["APP_ENV"] = "production"
        os.environ["SESSION_SECRET"] = "changeme-session-secret-min-32-chars"
        os.environ["CSRF_SECRET"] = "changeme-csrf-secret-min-32-chars"
        settings = config.Settings()
        try:
            settings.validate_secrets()
            assert False, "should raise"
        except RuntimeError:
            pass
    finally:
        if old_env is None:
            os.environ.pop("ENV", None)
        else:
            os.environ["ENV"] = old_env
        if old_app is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = old_app
        if old_session is None:
            os.environ.pop("SESSION_SECRET", None)
        else:
            os.environ["SESSION_SECRET"] = old_session
        if old_csrf is None:
            os.environ.pop("CSRF_SECRET", None)
        else:
            os.environ["CSRF_SECRET"] = old_csrf


def test_production_refuses_short_secrets() -> None:
    old_env = os.environ.get("ENV")
    old_app = os.environ.get("APP_ENV")
    old_session = os.environ.get("SESSION_SECRET")
    old_csrf = os.environ.get("CSRF_SECRET")
    try:
        os.environ["ENV"] = "production"
        os.environ["APP_ENV"] = "production"
        os.environ["SESSION_SECRET"] = "tooshort"
        os.environ["CSRF_SECRET"] = "alsotooshort"
        settings = config.Settings()
        try:
            settings.validate_secrets()
            assert False, "should raise"
        except RuntimeError:
            pass
    finally:
        if old_env is None:
            os.environ.pop("ENV", None)
        else:
            os.environ["ENV"] = old_env
        if old_app is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = old_app
        if old_session is None:
            os.environ.pop("SESSION_SECRET", None)
        else:
            os.environ["SESSION_SECRET"] = old_session
        if old_csrf is None:
            os.environ.pop("CSRF_SECRET", None)
        else:
            os.environ["CSRF_SECRET"] = old_csrf


def test_development_accepts_defaults() -> None:
    old_env = os.environ.get("ENV")
    old_app = os.environ.get("APP_ENV")
    try:
        os.environ["ENV"] = "development"
        os.environ["APP_ENV"] = "development"
        settings = config.Settings()
        settings.validate_secrets()
    finally:
        if old_env is None:
            os.environ.pop("ENV", None)
        else:
            os.environ["ENV"] = old_env
        if old_app is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = old_app
