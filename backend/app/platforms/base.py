"""Shared platform-adapter primitives."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlsplit

import httpx

from app.models.social import (
    SocialComment,
    SocialFetchRequest,
    SocialFetchResponse,
    SocialPlatform,
)

_URL_RE = re.compile(r"https?://[^\s\u3000]+")
_COUNT_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*(万|亿|w|k|m)?", re.IGNORECASE)

PLATFORM_LABELS = {
    SocialPlatform.XIAOHONGSHU: "小红书",
    SocialPlatform.DOUYIN: "抖音",
    SocialPlatform.BILIBILI: "Bilibili",
}

LOGIN_COMMANDS = {
    SocialPlatform.XIAOHONGSHU: r"scripts\social-login.bat xiaohongshu",
    SocialPlatform.DOUYIN: r"scripts\social-login.bat douyin",
    SocialPlatform.BILIBILI: r"scripts\social-login.bat bilibili",
}


class SocialPlatformError(RuntimeError):
    """Base error translated into a structured API error."""

    code = "social_error"

    def __init__(
        self,
        message: str,
        *,
        platform: SocialPlatform | None = None,
        hint: str = "",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.platform = platform
        self.hint = hint


class PlatformDetectError(SocialPlatformError):
    code = "unsupported_platform"


class PlatformAuthRequired(SocialPlatformError):
    code = "platform_auth_required"


class PlatformContentNotFound(SocialPlatformError):
    code = "content_not_found"


class PlatformFetchError(SocialPlatformError):
    code = "platform_fetch_failed"


class PlatformAccessBlocked(SocialPlatformError):
    """The platform served a security/CAPTCHA wall; the saved session may be
    valid, so this must not be reported as an expired cookie."""

    code = "platform_access_blocked"


class SocialAdapter(Protocol):
    platform: SocialPlatform

    def can_handle(self, url: str) -> bool: ...

    async def fetch(self, request: SocialFetchRequest) -> SocialFetchResponse: ...


def extract_first_url(text: str) -> str:
    match = _URL_RE.search(text)
    if not match:
        raise PlatformDetectError("没有识别到有效链接")
    return match.group(0).rstrip("，。,.；;）)】]")


def detect_platform(url: str) -> SocialPlatform:
    hostname = (urlsplit(url).hostname or "").lower()
    if hostname == "xhslink.com" or hostname.endswith(".xhslink.com"):
        return SocialPlatform.XIAOHONGSHU
    if hostname == "xiaohongshu.com" or hostname.endswith(".xiaohongshu.com"):
        return SocialPlatform.XIAOHONGSHU
    if hostname == "douyin.com" or hostname.endswith(".douyin.com"):
        return SocialPlatform.DOUYIN
    if hostname == "iesdouyin.com" or hostname.endswith(".iesdouyin.com"):
        return SocialPlatform.DOUYIN
    if hostname == "b23.tv" or hostname.endswith(".b23.tv"):
        return SocialPlatform.BILIBILI
    if hostname == "bilibili.com" or hostname.endswith(".bilibili.com"):
        return SocialPlatform.BILIBILI
    raise PlatformDetectError("目前仅支持小红书、抖音、Bilibili 链接")


def parse_count(value: Any) -> int:
    """Parse platform counters such as 1234, "1.2万", "3.4w", or "10万+"."""
    if value is None or value == "":
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().replace(",", "").replace("+", "")
    if not text or text in {"-", "赞", "评论"}:
        return 0
    match = _COUNT_RE.search(text)
    if not match:
        return 0
    number = float(match.group(1))
    unit = (match.group(2) or "").lower()
    multiplier = {
        "万": 10_000,
        "w": 10_000,
        "亿": 100_000_000,
        "k": 1_000,
        "m": 1_000_000,
        "": 1,
    }.get(unit, 1)
    return int(number * multiplier)


def count_comment_tree(comments: list[SocialComment]) -> int:
    """Count top-level comments plus nested replies."""
    return sum(1 + count_comment_tree(comment.replies) for comment in comments)


def timestamp_to_datetime(value: Any) -> datetime | None:
    """Convert seconds or milliseconds from platform APIs to UTC datetime."""
    if value is None or value == "":
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric > 10_000_000_000:
        numeric /= 1000
    try:
        return datetime.fromtimestamp(numeric, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return None


def find_first_dict(value: Any, predicate) -> dict[str, Any] | None:
    """Depth-first search for the first matching dict in nested API JSON."""
    if isinstance(value, dict):
        if predicate(value):
            return value
        for child in value.values():
            found = find_first_dict(child, predicate)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_first_dict(child, predicate)
            if found is not None:
                return found
    return None


async def resolve_short_url(url: str, timeout: float = 15.0) -> str:
    """Resolve platform short links when possible; fall back to original URL."""
    if not any(host in url for host in ("b23.tv", "v.douyin.com", "xhslink.com")):
        return url
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/131 Safari/537.36"
        )
    }
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers=headers,
        ) as client:
            response = await client.get(url)
            return str(response.url)
    except httpx.HTTPError:
        return url
