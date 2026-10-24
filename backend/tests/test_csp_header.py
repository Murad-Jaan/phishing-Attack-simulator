from fastapi.testclient import TestClient
from app.main import app
from app.core.csp import build_csp

client = TestClient(app)


def test_csp_header_development(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    response = client.get("/health")
    csp_header = response.headers.get("Content-Security-Policy", "")
    expected = build_csp("development")
    assert csp_header == expected


def test_csp_header_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    response = client.get("/health")
    csp_header = response.headers.get("Content-Security-Policy", "")
    assert "nonce-" in csp_header
    assert "unsafe-inline" not in csp_header
    assert "unsafe-eval" not in csp_header
    build_csp("production", "testnonce")
    assert "default-src 'self'" in csp_header
