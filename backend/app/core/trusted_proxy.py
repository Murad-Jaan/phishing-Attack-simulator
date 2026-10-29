import ipaddress

from fastapi import Request

from app.core.config import settings


def get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        return request.client.host if request.client else None

    client_host = request.client.host if request.client else None
    if not client_host:
        return None

    try:
        client_ip = ipaddress.ip_address(client_host)
    except Exception:
        return client_host

    allowed = settings.TRUSTED_PROXY_ALLOW_LOOPBACK and client_ip.is_loopback
    if not allowed and settings.TRUSTED_PROXY_NETWORKS:
        for network in settings.TRUSTED_PROXY_NETWORKS.split(","):
            network = network.strip()
            if not network:
                continue
            try:
                net = ipaddress.ip_network(network)
                if client_ip in net:
                    allowed = True
                    break
            except Exception:
                continue

    if not allowed:
        return client_host

    parts = [p.strip() for p in forwarded.split(",")]
    if not parts:
        return client_host
    return parts[0]
