import time
from unittest.mock import patch

from fastapi import Response

from app.core import csrf


def test_prelogin_csrf_accept_and_reject() -> None:
    resp = Response()
    token = csrf.issue_login_csrf(resp)
    assert csrf.verify_csrf_token(token, session_id=None) is True
    assert csrf.verify_csrf_token("bad.token", session_id=None) is False
    assert csrf.verify_csrf_token("a.b", session_id=None) is False
    # expired
    with patch("app.core.csrf.time") as mock_time:
        mock_time.time.return_value = time.time() + 10000
        assert csrf.verify_csrf_token(token, session_id=None) is False


def test_session_bound_csrf() -> None:
    resp = Response()
    token = csrf.issue_session_csrf(resp, "sessA")
    assert csrf.verify_csrf_token(token, session_id="sessA") is True
    assert csrf.verify_csrf_token(token, session_id="sessB") is False


def test_origin_referer_checks() -> None:
    from fastapi import Request

    scope = {
        "type": "http",
        "method": "POST",
        "headers": [(b"origin", b"http://127.0.0.1:3000")],
    }
    req = Request(scope)
    assert csrf.check_origin(req) is True

    scope = {
        "type": "http",
        "method": "POST",
        "headers": [(b"origin", b"http://evil.com")],
    }
    req = Request(scope)
    assert csrf.check_origin(req) is False

    scope = {
        "type": "http",
        "method": "POST",
        "headers": [(b"referer", b"http://127.0.0.1:3000/some/path")],
    }
    req = Request(scope)
    assert csrf.check_origin(req) is True

    scope = {"type": "http", "method": "POST", "headers": []}
    req = Request(scope)
    assert csrf.check_origin(req) is False

    scope = {"type": "http", "method": "GET", "headers": []}
    req = Request(scope)
    assert csrf.check_origin(req) is False


def test_csrf_uses_compare_digest() -> None:
    with patch("app.core.csrf.compare_digest_bytes") as mock_cd:
        mock_cd.return_value = True
        resp = Response()
        token = csrf.issue_session_csrf(resp, "sessA")
        csrf.verify_csrf_token(token, session_id="sessA")
        assert mock_cd.called
