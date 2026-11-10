"""Repeatable browser smoke test for the goodnews UI.

Prerequisites:
  * backend on http://127.0.0.1:8000
  * frontend dev server on http://127.0.0.1:5173
  * Python Playwright installed (backend venv)

Run from the repository root:
    backend\\.venv\\Scripts\\python.exe scripts\\ui-smoke.py
"""

from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import Browser, Playwright, sync_playwright

BASE_URL = os.getenv("GOODNEWS_WEB_URL", "http://127.0.0.1:5173")
CLAIM = "\u57c3\u83f2\u5c14\u94c1\u5854\u4f4d\u4e8e\u67cf\u6797\u3002"
OUTPUT_DIR = Path("docs/screenshots")


def launch_browser(playwright: Playwright) -> Browser:
    try:
        return playwright.chromium.launch(channel="msedge", headless=True)
    except Exception:
        return playwright.chromium.launch(headless=True)


def main() -> int:
    errors: list[str] = []
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on(
            "console",
            lambda message: errors.append(f"{message.type}: {message.text}")
            if message.type == "error"
            else None,
        )
        page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))

        page.goto(BASE_URL, wait_until="networkidle", timeout=30_000)
        page.wait_for_timeout(800)
        print("home:", page.locator("h1").first.inner_text().replace("\n", " / "))
        page.screenshot(path=str(OUTPUT_DIR / "01-home.png"), full_page=True)

        page.get_by_role("link", name="\u70ed\u70b9\u63a2\u7d22").click()
        page.wait_for_selector(".result-card", timeout=60_000)
        print("hot results:", page.locator(".result-card").count())
        page.screenshot(path=str(OUTPUT_DIR / "02-explore.png"), full_page=True)

        page.locator(".result-card__action").first.click()
        page.wait_for_timeout(800)
        prefilled = page.locator("textarea").input_value()
        assert prefilled.startswith("http"), "fact-check link was not prefilled"
        page.locator("textarea").fill(CLAIM)
        page.get_by_role("button", name="\u5f00\u59cb\u6838\u67e5").click()
        page.wait_for_selector(".verdict-card", timeout=180_000)
        page.wait_for_timeout(1000)
        print("verdict:", page.locator(".verdict-card h2").inner_text())
        print("claims:", page.locator(".claim").count())
        print("evidence:", page.locator(".evidence-item").count())
        print("graph:", page.locator(".graph-card .el-tag").first.inner_text())
        page.screenshot(path=str(OUTPUT_DIR / "03-report.png"), full_page=True)
        browser.close()

    print("console errors:", len(errors))
    for item in errors[:10]:
        print(item)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
