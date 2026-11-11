"""Social platform login-session lifecycle.

A login button starts a visible Edge window. The manager waits for the
platform's login cookie to appear, then writes a Playwright storage-state file.
The same file is consumed by the platform adapters on every fetch.

This is a best-effort session keeper: platforms control cookie lifetime, so a
forced logout can still require a new QR login. The manager detects expiry and
periodically visits the platform headlessly to let the platform refresh its own
session cookies.
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from app.core.config import Settings
from app.models.social import (
    SocialAuthState,
    SocialAuthStatus,
    SocialAuthStatusListResponse,
    SocialPlatform,
)
from app.platforms.browser import storage_state_path

logger = logging.getLogger(__name__)

LOGIN_URLS = {
    SocialPlatform.XIAOHONGSHU: "https://www.xiaohongshu.com/explore",
    SocialPlatform.DOUYIN: "https://www.douyin.com/",
    SocialPlatform.BILIBILI: "https://passport.bilibili.com/login",
}

HOME_URLS = {
    SocialPlatform.XIAOHONGSHU: "https://www.xiaohongshu.com/explore",
    SocialPlatform.DOUYIN: "https://www.douyin.com/",
    SocialPlatform.BILIBILI: "https://www.bilibili.com/",
}

LOGIN_COOKIE_NAMES = {
    SocialPlatform.XIAOHONGSHU: {"web_session"},
    SocialPlatform.DOUYIN: {"sessionid", "sessionid_ss", "sid_guard"},
    SocialPlatform.BILIBILI: {"SESSDATA"},
}


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


class SocialAuthManager:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._waiting: dict[SocialPlatform, SocialAuthStatus] = {}
        self._login_tasks: dict[SocialPlatform, asyncio.Task[None]] = {}
        self._keeper_task: asyncio.Task[None] | None = None
        self._closed = False

    # Paths ---------------------------------------------------------------
    def _state_path(self, platform: SocialPlatform) -> Path:
        return storage_state_path(self._settings, platform)

    def _meta_path(self, platform: SocialPlatform) -> Path:
        return self._state_path(platform).with_suffix(".meta.json")

    def _read_meta(self, platform: SocialPlatform) -> dict[str, Any]:
        path = self._meta_path(platform)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_meta(self, platform: SocialPlatform, payload: dict[str, Any]) -> None:
        path = self._meta_path(platform)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _delete_session(self, platform: SocialPlatform) -> None:
        self._state_path(platform).unlink(missing_ok=True)
        self._meta_path(platform).unlink(missing_ok=True)
        self._waiting.pop(platform, None)

    # Status --------------------------------------------------------------
    def _expiry_from_state(self, platform: SocialPlatform) -> datetime | None:
        path = self._state_path(platform)
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        cookies = state.get("cookies") or []
        important_names = LOGIN_COOKIE_NAMES[platform]
        candidates = [
            float(cookie["expires"])
            for cookie in cookies
            if isinstance(cookie, dict)
            and cookie.get("name") in important_names
            and isinstance(cookie.get("expires"), (int, float))
            and float(cookie["expires"]) > 0
        ]
        if not candidates:
            candidates = [
                float(cookie["expires"])
                for cookie in cookies
                if isinstance(cookie, dict)
                and isinstance(cookie.get("expires"), (int, float))
                and float(cookie["expires"]) > 0
            ]
        if not candidates:
            return None
        try:
            return datetime.fromtimestamp(min(candidates), tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None

    def status(self, platform: SocialPlatform) -> SocialAuthStatus:
        waiting = self._waiting.get(platform)
        if waiting and waiting.state in {
            SocialAuthState.WAITING,
            SocialAuthState.FAILED,
        }:
            waiting.last_checked_at = _now()
            return waiting

        state_path = self._state_path(platform)
        meta = self._read_meta(platform)
        if not state_path.exists():
            return SocialAuthStatus(
                platform=platform,
                state=SocialAuthState.NOT_LOGGED_IN,
                message="未登录。Bilibili/抖音公开内容仍可直接采集，小红书需要登录。",
                last_checked_at=_now(),
            )

        expires_at = self._expiry_from_state(platform)
        expired_at = _parse_dt(meta.get("expired_at"))
        if expired_at is not None or (expires_at is not None and expires_at <= _now()):
            return SocialAuthStatus(
                platform=platform,
                state=SocialAuthState.EXPIRED,
                message="登录态已过期，请重新登录。",
                account_name=meta.get("account_name"),
                expires_at=expires_at,
                last_login_at=_parse_dt(meta.get("last_login_at")),
                last_checked_at=_now(),
                last_refreshed_at=_parse_dt(meta.get("last_refreshed_at")),
            )

        return SocialAuthStatus(
            platform=platform,
            state=SocialAuthState.LOGGED_IN,
            logged_in=True,
            account_name=meta.get("account_name"),
            message="登录态已保存，采集时会自动使用。",
            expires_at=expires_at,
            last_login_at=_parse_dt(meta.get("last_login_at")),
            last_checked_at=_now(),
            last_refreshed_at=_parse_dt(meta.get("last_refreshed_at")),
        )

    def status_all(self) -> SocialAuthStatusListResponse:
        return SocialAuthStatusListResponse(
            statuses=[self.status(platform) for platform in SocialPlatform]
        )

    # Login ---------------------------------------------------------------
    async def start_login(self, platform: SocialPlatform) -> SocialAuthStatus:
        existing = self._login_tasks.get(platform)
        if existing and not existing.done():
            return self.status(platform)
        status = SocialAuthStatus(
            platform=platform,
            state=SocialAuthState.WAITING,
            message="登录窗口已打开，请在浏览器中完成扫码或账号登录。",
            last_checked_at=_now(),
        )
        self._waiting[platform] = status
        self._login_tasks[platform] = asyncio.create_task(self._login_flow(platform))
        return status

    async def _login_flow(self, platform: SocialPlatform) -> None:
        state_path = self._state_path(platform)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            async with async_playwright() as playwright:
                launch_options: dict[str, Any] = {"headless": False}
                if self._settings.playwright_browser_channel:
                    launch_options["channel"] = self._settings.playwright_browser_channel
                browser = await playwright.chromium.launch(**launch_options)
                context_args: dict[str, Any] = {
                    "viewport": {"width": 1440, "height": 1000},
                    "locale": "zh-CN",
                    "timezone_id": "Asia/Shanghai",
                }
                if state_path.exists():
                    context_args["storage_state"] = str(state_path)
                context = await browser.new_context(**context_args)
                page = await context.new_page()
                await page.goto(
                    LOGIN_URLS[platform],
                    wait_until="domcontentloaded",
                    timeout=self._settings.social_browser_timeout_ms,
                )
                deadline = asyncio.get_running_loop().time() + self._settings.social_login_timeout_seconds
                while asyncio.get_running_loop().time() < deadline:
                    cookies = await context.cookies()
                    if self._has_login_cookie(platform, cookies):
                        await page.wait_for_timeout(1_200)
                        await context.storage_state(path=str(state_path))
                        account_name = await self._detect_account(platform, cookies)
                        now = _now()
                        self._write_meta(
                            platform,
                            {
                                "account_name": account_name,
                                "last_login_at": _iso(now),
                                "last_refreshed_at": _iso(now),
                                "expired_at": None,
                            },
                        )
                        self._waiting[platform] = SocialAuthStatus(
                            platform=platform,
                            state=SocialAuthState.LOGGED_IN,
                            logged_in=True,
                            account_name=account_name,
                            message="登录成功，登录态已保存。",
                            expires_at=self._expiry_from_state(platform),
                            last_login_at=now,
                            last_checked_at=now,
                            last_refreshed_at=now,
                        )
                        return
                    await asyncio.sleep(2)
                self._waiting[platform] = SocialAuthStatus(
                    platform=platform,
                    state=SocialAuthState.FAILED,
                    message="登录等待超时，请重新点击登录。",
                    last_checked_at=_now(),
                )
        except asyncio.CancelledError:
            self._waiting[platform] = SocialAuthStatus(
                platform=platform,
                state=SocialAuthState.NOT_LOGGED_IN,
                message="登录已取消。",
                last_checked_at=_now(),
            )
            raise
        except Exception as exc:
            logger.exception("Social login failed for %s", platform.value)
            self._waiting[platform] = SocialAuthStatus(
                platform=platform,
                state=SocialAuthState.FAILED,
                message=f"打开登录窗口失败：{exc}",
                last_checked_at=_now(),
            )
        finally:
            self._login_tasks.pop(platform, None)

    @staticmethod
    def _has_login_cookie(platform: SocialPlatform, cookies: list[dict[str, Any]]) -> bool:
        names = {str(cookie.get("name", "")) for cookie in cookies}
        return bool(names & LOGIN_COOKIE_NAMES[platform])

    async def _detect_account(
        self, platform: SocialPlatform, cookies: list[dict[str, Any]]
    ) -> str | None:
        if platform is not SocialPlatform.BILIBILI:
            return None
        cookie_header = "; ".join(
            f"{cookie['name']}={cookie['value']}"
            for cookie in cookies
            if cookie.get("name") and cookie.get("value") is not None
        )
        try:
            import httpx

            async with httpx.AsyncClient(
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131",
                    "Cookie": cookie_header,
                    "Referer": "https://www.bilibili.com/",
                },
                timeout=15,
            ) as client:
                payload = (await client.get("https://api.bilibili.com/x/web-interface/nav")).json()
            data = payload.get("data") or {}
            if data.get("isLogin"):
                return str(data.get("uname") or "Bilibili 账号")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Bilibili account detection failed: %s", exc)
        return "Bilibili 账号"

    async def logout(self, platform: SocialPlatform) -> SocialAuthStatus:
        task = self._login_tasks.pop(platform, None)
        if task and not task.done():
            task.cancel()
            # Do not block the HTTP response on Edge/Playwright teardown.
            await asyncio.wait({task}, timeout=0.6)
        self._delete_session(platform)
        return self.status(platform)

    def mark_expired(self, platform: SocialPlatform) -> None:
        meta = self._read_meta(platform)
        meta["expired_at"] = _iso(_now())
        self._write_meta(platform, meta)
        self._waiting.pop(platform, None)

    # Refresh / keepalive -------------------------------------------------
    async def refresh(self, platform: SocialPlatform) -> SocialAuthStatus:
        state_path = self._state_path(platform)
        if not state_path.exists():
            return self.status(platform)
        try:
            async with async_playwright() as playwright:
                launch_options: dict[str, Any] = {
                    "headless": self._settings.social_browser_headless
                }
                if self._settings.playwright_browser_channel:
                    launch_options["channel"] = self._settings.playwright_browser_channel
                browser = await playwright.chromium.launch(**launch_options)
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 900},
                    locale="zh-CN",
                    timezone_id="Asia/Shanghai",
                    storage_state=str(state_path),
                )
                page = await context.new_page()
                await page.goto(
                    HOME_URLS[platform],
                    wait_until="domcontentloaded",
                    timeout=self._settings.social_browser_timeout_ms,
                )
                await page.wait_for_timeout(1_500)
                await context.storage_state(path=str(state_path))
                await browser.close()
            meta = self._read_meta(platform)
            meta["last_refreshed_at"] = _iso(_now())
            meta.pop("expired_at", None)
            self._write_meta(platform, meta)
        except Exception as exc:  # noqa: BLE001
            logger.info("Session refresh skipped for %s: %s", platform.value, exc)
        return self.status(platform)

    def start_background(self) -> None:
        if self._keeper_task is None or self._keeper_task.done():
            self._keeper_task = asyncio.create_task(self._keepalive_loop())

    async def _keepalive_loop(self) -> None:
        interval = max(1, self._settings.social_keepalive_hours) * 3600
        while True:
            await asyncio.sleep(interval)
            if self._closed:
                return
            for platform in SocialPlatform:
                if self.status(platform).logged_in:
                    await self.refresh(platform)

    async def close(self) -> None:
        self._closed = True
        if self._keeper_task:
            self._keeper_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._keeper_task
        for task in list(self._login_tasks.values()):
            task.cancel()
        for task in list(self._login_tasks.values()):
            with suppress(asyncio.CancelledError):
                await task
        self._login_tasks.clear()
