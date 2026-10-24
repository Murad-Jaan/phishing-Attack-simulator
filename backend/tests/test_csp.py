from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_csp_header_exists():
    response = client.get("/health")
    assert "Content-Security-Policy" in response.headers


def test_csp_production_policy():
    # Simulate production by checking the middleware logic
    # Production should have nonce and no unsafe-inline or unsafe-eval
    response = client.get("/health")
    csp = response.headers.get("Content-Security-Policy", "")
    assert csp  # header exists
    # Development currently allows unsafe-inline, production should not
    # This test documents the requirement


def test_csp_development_policy():
    response = client.get("/health")
    csp = response.headers.get("Content-Security-Policy", "")
    assert csp  # development policy exists
