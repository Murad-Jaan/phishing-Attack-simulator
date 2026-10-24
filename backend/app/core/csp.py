def build_csp(env: str = "development", nonce: str = "") -> str:
    if env == "production":
        if not nonce:
            raise ValueError("nonce required in production")
        csp = f"default-src 'self'; script-src 'nonce-{nonce}' 'strict-dynamic'; style-src 'self' 'nonce-{nonce}'; object-src 'none'; base-uri 'self';"
        return csp
    else:
        return "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
