"""HTML -> article text extraction shared by Scrapy spiders and tests."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlsplit

import trafilatura
from parsel import Selector


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def extract_article_from_html(html: str, url: str) -> dict[str, Any]:
    """Extract main text and metadata with trafilatura.

    If trafilatura cannot identify a main body (common for short or unusual
    pages), fall back to visible text from article/main/body in that order.
    The fallback is still trafilatura-first rather than a home-grown HTML
    regex parser.
    """
    text = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=False,
        favor_recall=True,
    ) or ""

    metadata = trafilatura.extract_metadata(html, default_url=url)
    title = _clean(getattr(metadata, "title", ""))
    author = _clean(getattr(metadata, "author", "")) or None
    published_at = _clean(getattr(metadata, "date", "")) or None
    source_name = _clean(getattr(metadata, "sitename", "")) or (urlsplit(url).hostname or "")

    selector = Selector(text=html)
    if not title:
        title = _clean(
            selector.css('meta[property="og:title"]::attr(content)').get()
            or selector.css("title::text").get()
        )
    if len(text) < 120:
        fallback_parts = selector.xpath(
            "//article//text()[not(ancestor::script) and not(ancestor::style)]"
        ).getall()
        if not fallback_parts:
            fallback_parts = selector.xpath(
                "//main//text()[not(ancestor::script) and not(ancestor::style)]"
            ).getall()
        if not fallback_parts:
            fallback_parts = selector.xpath(
                "//body//text()[not(ancestor::script) and not(ancestor::style)]"
            ).getall()
        fallback_text = _clean(" ".join(fallback_parts))
        if len(fallback_text) > len(text):
            text = fallback_text

    # Some publishers embed JSON-LD with a cleaner date/author than meta tags.
    if not published_at:
        for raw in selector.css('script[type="application/ld+json"]::text').getall():
            try:
                payload = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            candidates = payload if isinstance(payload, list) else [payload]
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                published_at = _clean(candidate.get("datePublished")) or None
                if published_at:
                    break
            if published_at:
                break

    return {
        "title": title or "未命名文章",
        "text": text.strip(),
        "author": author,
        "published_at": published_at,
        "source_name": source_name,
        "url": url,
    }
