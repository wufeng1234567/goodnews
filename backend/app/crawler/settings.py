"""Scrapy settings for the goodnews article crawler."""

from __future__ import annotations

from typing import Any

BOT_NAME = "goodnews"

BASE_SETTINGS: dict[str, Any] = {
    "BOT_NAME": BOT_NAME,
    "SPIDER_MODULES": ["app.crawler.spiders"],
    "NEWSPIDER_MODULE": "app.crawler.spiders",
    "USER_AGENT": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36 "
        "goodnews-factcheck/0.1"
    ),
    # MVP: public news pages are often behind robots rules that block feed
    # readers. This is a conscious demo trade-off; production must revisit it.
    "ROBOTSTXT_OBEY": False,
    "COOKIES_ENABLED": False,
    "TELNETCONSOLE_ENABLED": False,
    "DOWNLOAD_TIMEOUT": 25,
    "DOWNLOAD_DELAY": 0.25,
    "CONCURRENT_REQUESTS": 4,
    "LOG_LEVEL": "ERROR",
    "FEED_EXPORT_ENCODING": "utf-8",
    "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7",
    "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
    "RETRY_TIMES": 1,
}


def build_scrapy_settings(
    use_playwright: bool,
    timeout_ms: int,
    browser_channel: str = "",
) -> dict[str, Any]:
    settings = dict(BASE_SETTINGS)
    if use_playwright:
        launch_options: dict[str, Any] = {"headless": True}
        if browser_channel:
            launch_options["channel"] = browser_channel
        settings.update(
            {
                "DOWNLOAD_HANDLERS": {
                    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
                    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
                },
                "PLAYWRIGHT_BROWSER_TYPE": "chromium",
                "PLAYWRIGHT_LAUNCH_OPTIONS": launch_options,
                "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": timeout_ms,
                "PLAYWRIGHT_ABORT_REQUEST": lambda request: request.resource_type
                in {"image", "media", "font"},
            }
        )
    return settings
