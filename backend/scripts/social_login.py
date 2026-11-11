"""Open a platform in Edge and save a local Playwright login state.

Usage (from backend/):
    .venv\\Scripts\\python.exe scripts/social_login.py xiaohongshu
    .venv\\Scripts\\python.exe scripts/social_login.py douyin
    .venv\\Scripts\\python.exe scripts/social_login.py bilibili

The state file is written to backend/.browser-profiles/<platform>.json and is
git-ignored. It contains cookies, so treat it like a password.
"""

from __future__ import annotations

import argparse
import asyncio

from playwright.async_api import async_playwright

from app.core.config import get_settings
from app.models.social import SocialPlatform

PLATFORM_URLS = {
    SocialPlatform.XIAOHONGSHU: "https://www.xiaohongshu.com/explore",
    SocialPlatform.DOUYIN: "https://www.douyin.com/",
    SocialPlatform.BILIBILI: "https://www.bilibili.com/",
}


async def main(platform: SocialPlatform) -> int:
    settings = get_settings()
    state_path = settings.social_state_path / f"{platform.value}.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    launch_options: dict[str, object] = {"headless": False}
    if settings.playwright_browser_channel:
        launch_options["channel"] = settings.playwright_browser_channel

    print(f"Opening {platform.value} for login...")
    print("Complete the login/QR-code flow in the browser window.")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**launch_options)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 1000},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        page = await context.new_page()
        await page.goto(PLATFORM_URLS[platform], wait_until="domcontentloaded", timeout=60_000)
        print(f"Current page: {page.url}")
        await asyncio.to_thread(input, "Press Enter here after you have logged in...")
        await context.storage_state(path=str(state_path))
        print(f"Saved login state: {state_path}")
        await browser.close()
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Save a social platform login state")
    parser.add_argument(
        "platform",
        choices=[platform.value for platform in SocialPlatform],
        help="Platform to log in to",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(SocialPlatform(parse_args().platform))))
