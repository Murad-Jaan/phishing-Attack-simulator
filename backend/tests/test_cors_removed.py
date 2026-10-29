from fastapi.testclient import TestClient

from app.main import app


def test_no_cors_allow_origin() -> None:
    client = TestClient(app)
    resp = client.get("/health", headers={"Origin": "http://evil.com"})
    assert "access-control-allow-origin" not in {k.lower() for k in resp.headers.keys()}
