from app.core.csp import build_csp


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


def test_csp_development_policy():
    csp = build_csp("development")
    assert "unsafe-inline" in csp  # explicitly looser policy


def test_csp_production_different_nonces():
    csp1 = build_csp("production", "nonce1")
    csp2 = build_csp("production", "nonce2")
    assert csp1 != csp2
