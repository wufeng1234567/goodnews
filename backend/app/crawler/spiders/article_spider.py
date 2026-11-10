"""Single-article Scrapy spider."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from typing import ClassVar

import scrapy

from app.crawler.extract import extract_article_from_html


class ArticleSpider(scrapy.Spider):
    name = "article"
    custom_settings: ClassVar[dict[str, str]] = {"LOG_LEVEL": "ERROR"}

    def __init__(self, url: str, use_playwright: bool = False, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.start_url = url
        self.use_playwright = bool(use_playwright)

    async def start(self) -> AsyncIterator[scrapy.Request]:
        """Scrapy 2.13+ async start hook (used by Scrapy 2.20)."""
        for request in self._build_requests():
            yield request

    def start_requests(self) -> Iterable[scrapy.Request]:
        """Legacy hook kept for older Scrapy versions."""
        return self._build_requests()

    def _build_requests(self) -> Iterable[scrapy.Request]:
        meta = {}
        if self.use_playwright:
            meta = {
                "playwright": True,
                "playwright_include_page": False,
                "playwright_page_goto_kwargs": {"wait_until": "domcontentloaded"},
            }
        yield scrapy.Request(
            url=self.start_url,
            callback=self.parse,
            errback=self.handle_error,
            meta=meta,
            dont_filter=True,
        )

    def parse(self, response: scrapy.http.Response, **kwargs):
        item = extract_article_from_html(response.text, response.url)
        if len(item.get("text", "")) < 80:
            self.logger.warning("Article body too short for %s", response.url)
            return
        yield item

    def handle_error(self, failure) -> None:
        self.logger.error("Article request failed for %s: %s", self.start_url, failure.value)
