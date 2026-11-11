"""Playwright browser session helpers for social platforms."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from playwright.async_api import Page, async_playwright

from app.core.config import Settings
from app.models.social import SocialPlatform

logger = logging.getLogger(__name__)

_PLATFORM_ORIGINS = {
    SocialPlatform.XIAOHONGSHU: "https://www.xiaohongshu.com",
    SocialPlatform.DOUYIN: "https://www.douyin.com",
    SocialPlatform.BILIBILI: "https://www.bilibili.com",
}


def storage_state_path(settings: Settings, platform: SocialPlatform) -> Path:
    return settings.social_state_path / f"{platform.value}.json"


def _cookie_header(settings: Settings, platform: SocialPlatform) -> str:
    secret = {
        SocialPlatform.XIAOHONGSHU: settings.xhs_cookie,
        SocialPlatform.DOUYIN: settings.douyin_cookie,
        SocialPlatform.BILIBILI: settings.bilibili_cookie,
    }[platform]
    return secret.get_secret_value().strip()


def _parse_cookie_header(raw: str, origin: str) -> list[dict[str, str]]:
    cookies: list[dict[str, str]] = []
    for part in raw.split(";"):
        pair = part.strip()
        if not pair or "=" not in pair:
            continue
        name, value = pair.split("=", 1)
        if name.strip():
            cookies.append(
                {
                    "name": name.strip(),
                    "value": value.strip(),
                    "url": origin,
                }
            )
    return cookies


@asynccontextmanager
async def open_browser_page(
    settings: Settings,
    platform: SocialPlatform,
) -> AsyncIterator[Page]:
    """Open an Edge/Chromium page with optional Cookie or saved login state."""
    state_path = storage_state_path(settings, platform)
    launch_options: dict[str, object] = {"headless": settings.social_browser_headless}
    if settings.playwright_browser_channel:
        launch_options["channel"] = settings.playwright_browser_channel

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**launch_options)
        context_options: dict[str, object] = {
            "viewport": {"width": 1440, "height": 1000},
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
            "extra_http_headers": {"Accept-Language": "zh-CN,zh;q=0.9"},
        }
        if state_path.exists():
            context_options["storage_state"] = str(state_path)
            logger.info("Using saved login state for %s", platform.value)
        context = await browser.new_context(**context_options)
        raw_cookie = _cookie_header(settings, platform)
        if raw_cookie:
            await context.add_cookies(
                _parse_cookie_header(raw_cookie, _PLATFORM_ORIGINS[platform])
            )
        page = await context.new_page()
        page.set_default_timeout(settings.social_browser_timeout_ms)
        try:
            yield page
        finally:
            await browser.close()


def storage_state_cookie_header(settings: Settings, platform: SocialPlatform) -> str:
    """Return a Cookie header from a saved Playwright storage state file."""
    path = storage_state_path(settings, platform)
    if not path.exists():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    cookies = payload.get("cookies") or []
    pairs = [
        f"{cookie['name']}={cookie['value']}"
        for cookie in cookies
        if isinstance(cookie, dict) and cookie.get("name") and cookie.get("value") is not None
    ]
    return "; ".join(pairs)


def cookie_header(settings: Settings, platform: SocialPlatform) -> str:
    """Storage state takes precedence over an optional deployment Cookie env."""
    return storage_state_cookie_header(settings, platform) or _cookie_header(settings, platform)


def auth_mode(settings: Settings, platform: SocialPlatform) -> str:
    if storage_state_path(settings, platform).exists():
        return "storage_state"
    if _cookie_header(settings, platform):
        return "cookie"
    return "none"


def login_required_message(platform: SocialPlatform) -> str:
    label = {
        SocialPlatform.XIAOHONGSHU: "小红书",
        SocialPlatform.DOUYIN: "抖音",
        SocialPlatform.BILIBILI: "Bilibili",
    }[platform]
    command = rf"scripts\social-login.bat {platform.value}"
    return (
        f"{label}返回了登录/安全验证页，当前匿名会话无法获取内容。"
        f"请先运行 {command} 完成扫码登录，然后重试。"
    )
