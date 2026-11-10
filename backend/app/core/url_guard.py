"""Outbound URL validation.

Fact-checking accepts arbitrary URLs, so every initial outbound request must
be checked against SSRF targets. This is deliberately a *pre-flight* guard:
redirects are handled by Scrapy's redirect middleware and are not re-validated
in the MVP. Later hardening point: add a Scrapy downloader middleware that
re-runs this check on every redirected request.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit


class URLGuardError(ValueError):
    """Raised when a URL is malformed or points at a non-public address."""


def _is_public_ip(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


async def assert_public_http_url(url: str) -> str:
    """Validate scheme/host and resolve DNS before the crawler touches the URL."""
    parsed = urlsplit(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise URLGuardError("仅支持 http/https 链接")
    if parsed.username or parsed.password:
        raise URLGuardError("链接不能包含用户名或密码")
    host = parsed.hostname
    if not host:
        raise URLGuardError("链接缺少有效域名")

    # ``localhost`` never needs a DNS lookup and is blocked by default.
    try:
        addresses = await asyncio.to_thread(
            socket.getaddrinfo, host, parsed.port or (443 if parsed.scheme == "https" else 80)
        )
    except socket.gaierror as exc:
        raise URLGuardError(f"域名解析失败: {host}") from exc

    resolved = {item[4][0] for item in addresses}
    if not resolved or any(not _is_public_ip(item) for item in resolved):
        raise URLGuardError("出于安全原因，不允许访问内网或本机地址")
    return url.strip()
