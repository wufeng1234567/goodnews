"""Standalone Scrapy runner.

Scrapy's Twisted reactor cannot be restarted inside a long-lived process. The
MVP therefore invokes this module in a short-lived child process per URL. It
writes one JSON record to ``--output`` and exits. Later refactor point: replace
with a dedicated crawler service or a managed Scrapy worker pool.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    # Must happen before Twisted imports select a reactor.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _run(
    url: str, use_playwright: bool, timeout_ms: int, browser_channel: str = ""
) -> dict[str, Any]:
    from scrapy import signals
    from scrapy.crawler import CrawlerProcess

    from app.crawler.settings import build_scrapy_settings
    from app.crawler.spiders.article_spider import ArticleSpider

    captured: list[dict[str, Any]] = []
    errors: list[str] = []

    process = CrawlerProcess(
        settings=build_scrapy_settings(
            use_playwright=use_playwright,
            timeout_ms=timeout_ms,
            browser_channel=browser_channel,
        )
    )
    crawler = process.create_crawler(ArticleSpider)

    def on_item_scraped(item, response, spider) -> None:
        captured.append(dict(item))

    def on_spider_error(failure, response, spider) -> None:
        errors.append(str(failure.value))

    crawler.signals.connect(on_item_scraped, signal=signals.item_scraped)
    crawler.signals.connect(on_spider_error, signal=signals.spider_error)
    process.crawl(crawler, url=url, use_playwright=use_playwright)
    process.start()

    if captured:
        return {"ok": True, "article": captured[0]}
    return {
        "ok": False,
        "error": errors[0] if errors else "未提取到正文（页面可能需要登录或为纯视频/图片页）",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch one article with Scrapy")
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--playwright", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=20_000)
    parser.add_argument("--browser-channel", default="")
    args = parser.parse_args()

    try:
        payload = _run(
            args.url,
            args.playwright,
            args.timeout_ms,
            browser_channel=args.browser_channel,
        )
    except Exception as exc:  # noqa: BLE001 - serialize failure for parent process
        payload = {"ok": False, "error": f"爬虫运行失败: {exc}"}

    output_path = Path(args.output)
    output_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
