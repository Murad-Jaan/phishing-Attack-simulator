import pytest
from fastapi.testclient import TestClient

from app.core.csp import build_csp
from app.main import app


def test_csp_header_exists():
    csp = build_csp("production", "abc123")
    assert csp


def test_csp_production_policy():
    nonce = "testnonce123"
    csp = build_csp("production", nonce)
    assert nonce in csp
    assert "default-src 'self'" in csp
    assert "unsafe-inline" not in csp
    assert "unsafe-eval" not in csp


def test_csp_production_policy_includes_strict_dynamic_object_src_and_base_uri():
    csp = build_csp("production", "abc123")
    assert "script-src 'nonce-abc123' 'strict-dynamic'" in csp
    assert "object-src 'none'" in csp
    assert "base-uri 'self'" in csp


def test_csp_production_requires_nonce():
    with pytest.raises(ValueError, match="nonce required in production"):
        build_csp("production")


def test_csp_theme_cookie_does_not_weaken_production_policy(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    client = TestClient(app)
    response = client.get("/health", cookies={"phishsim_theme": "dark"})
    csp = response.headers.get("Content-Security-Policy", "")
    assert "nonce-" in csp
    assert "'strict-dynamic'" in csp
    assert "unsafe-inline" not in csp
    assert "unsafe-eval" not in csp


def test_csp_development_policy():
    csp = build_csp("development")
    assert "unsafe-inline" in csp  # explicitly looser policy


def test_csp_production_different_nonces():
    csp1 = build_csp("production", "nonce1")
    csp2 = build_csp("production", "nonce2")
    assert csp1 != csp2
