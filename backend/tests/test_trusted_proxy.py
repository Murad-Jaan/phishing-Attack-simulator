from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core import trusted_proxy


def test_untrusted_ignores_forwarded_header() -> None:
    app = FastAPI()

    @app.get("/ip")
    def get_ip(request: Request):
        return {"ip": trusted_proxy.get_client_ip(request)}

    client = TestClient(app)
    scope = {"type": "http", "method": "GET", "headers": [(b"x-forwarded-for", b"1.2.3.4")], "client": ("192.168.1.100", 1234)}
    req = Request(scope)
    assert trusted_proxy.get_client_ip(req) == "192.168.1.100"


def test_trusted_network_uses_forwarded() -> None:
    import os

    old_net = os.environ.get("TRUSTED_PROXY_NETWORKS")
    old_loop = os.environ.get("TRUSTED_PROXY_ALLOW_LOOPBACK")
    os.environ["TRUSTED_PROXY_NETWORKS"] = "192.168.0.0/16"
    os.environ["TRUSTED_PROXY_ALLOW_LOOPBACK"] = "false"
    try:
        from app.core import config

        config.settings.TRUSTED_PROXY_NETWORKS = "192.168.0.0/16"
        config.settings.TRUSTED_PROXY_ALLOW_LOOPBACK = False
        scope = {"type": "http", "method": "GET", "headers": [(b"x-forwarded-for", b"1.2.3.4, 5.6.7.8")], "client": ("192.168.1.100", 1234)}
        req = Request(scope)
        assert trusted_proxy.get_client_ip(req) == "1.2.3.4"
    finally:
        if old_net is None:
            os.environ.pop("TRUSTED_PROXY_NETWORKS", None)
        else:
            os.environ["TRUSTED_PROXY_NETWORKS"] = old_net
        if old_loop is None:
            os.environ.pop("TRUSTED_PROXY_ALLOW_LOOPBACK", None)
        else:
            os.environ["TRUSTED_PROXY_ALLOW_LOOPBACK"] = old_loop
        from app.core import config

        config.settings.TRUSTED_PROXY_NETWORKS = old_net or ""
        config.settings.TRUSTED_PROXY_ALLOW_LOOPBACK = True


def test_malformed_forwarded_falls_back() -> None:
    scope = {"type": "http", "method": "GET", "headers": [(b"x-forwarded-for", b"not-an-ip")], "client": ("192.168.1.100", 1234)}
    req = Request(scope)
    assert trusted_proxy.get_client_ip(req) == "192.168.1.100"


def test_production_empty_trusted_list_trusts_nothing() -> None:
    import os

    old_env = os.environ.get("ENV")
    old_app = os.environ.get("APP_ENV")
    old_net = os.environ.get("TRUSTED_PROXY_NETWORKS")
    old_loop = os.environ.get("TRUSTED_PROXY_ALLOW_LOOPBACK")
    os.environ["ENV"] = "production"
    os.environ["APP_ENV"] = "production"
    os.environ["TRUSTED_PROXY_NETWORKS"] = ""
    os.environ["TRUSTED_PROXY_ALLOW_LOOPBACK"] = "false"
    try:
        from app.core import config

        config.settings.ENV = "production"
        config.settings.APP_ENV = "production"
        config.settings.TRUSTED_PROXY_NETWORKS = ""
        config.settings.TRUSTED_PROXY_ALLOW_LOOPBACK = False
        scope = {"type": "http", "method": "GET", "headers": [(b"x-forwarded-for", b"1.2.3.4")], "client": ("10.0.0.5", 1234)}
        req = Request(scope)
        assert trusted_proxy.get_client_ip(req) == "10.0.0.5"
    finally:
        if old_env is None:
            os.environ.pop("ENV", None)
        else:
            os.environ["ENV"] = old_env
        if old_app is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = old_app
        if old_net is None:
            os.environ.pop("TRUSTED_PROXY_NETWORKS", None)
        else:
            os.environ["TRUSTED_PROXY_NETWORKS"] = old_net
        if old_loop is None:
            os.environ.pop("TRUSTED_PROXY_ALLOW_LOOPBACK", None)
        else:
            os.environ["TRUSTED_PROXY_ALLOW_LOOPBACK"] = old_loop
        from app.core import config

        config.settings.ENV = old_env or "development"
        config.settings.APP_ENV = old_app or "development"
        config.settings.TRUSTED_PROXY_NETWORKS = old_net or ""
        config.settings.TRUSTED_PROXY_ALLOW_LOOPBACK = True
