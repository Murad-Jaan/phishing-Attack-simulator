from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import generic_exception_handler, validation_exception_handler
from fastapi.exceptions import RequestValidationError


def test_validation_error_envelope() -> None:
    app = FastAPI()
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore

    @app.middleware("http")
    async def add_rid(request, call_next):
        request.state.request_id = "req-abc"
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.get("/test")
    def test_ep(x: int):
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/test")
    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
    assert "fields" in data["error"]
    assert "request_id" in data["error"]
    assert resp.headers.get("x-request-id") is not None
    assert resp.headers.get("x-request-id") == data["error"]["request_id"]


def test_generic_exception_no_internals() -> None:
    app = FastAPI()

    @app.middleware("http")
    async def add_rid(request, call_next):
        request.state.request_id = "req-123"
        response = await call_next(request)
        response.headers["X-Request-ID"] = "req-123"
        return response

    app.add_exception_handler(Exception, generic_exception_handler)  # type: ignore

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret internal detail")

    @app.exception_handler(Exception)
    async def _exh(request, exc):
        from app.core import errors

        return await errors.generic_exception_handler(request, exc)

    client = TestClient(app)
    resp = client.get("/boom")
    assert resp.status_code == 500
    data = resp.json()
    assert data["error"]["code"] == "internal_error"
    assert data["error"]["request_id"] == "req-123"
    body = resp.text
    assert "secret internal detail" not in body
    assert "RuntimeError" not in body
    assert "boom" not in body
    assert "Traceback" not in body
    assert "internal server error" in data["error"]["message"].lower()
    assert resp.headers.get("x-request-id") == "req-123"
    assert resp.headers.get("x-request-id") == data["error"]["request_id"]
