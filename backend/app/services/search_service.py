"""News search using public RSS endpoints.

No search API key is required for the MVP. The provider is intentionally
behind an interface so a paid search API can be added later without touching
the LangGraph nodes. RSS is external untrusted data; all fields are parsed as
plain text and never executed.
"""

from __future__ import annotations

import hashlib
import html
import logging
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from urllib.parse import quote_plus, urlsplit

import httpx
from googlenewsdecoder import GoogleDecoderAsync

from app.core.config import Settings
from app.models.search import HotNewsResponse, SearchResponse, SearchResultItem
from app.services.cache import RedisCache

logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r"<[^>]+>")


class SearchUnavailableError(RuntimeError):
    """All configured RSS providers failed."""


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", html.unescape(_HTML_TAG_RE.sub(" ", value))).strip()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(node: ET.Element, name: str) -> str:
    for child in node:
        if _local_name(child.tag) == name:
            return child.text or ""
    return ""


def _stable_id(url: str) -> str:
    return "news-" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


class RSSNewsProvider:
    """One concrete public RSS provider (Google News or Bing News)."""

    def __init__(self, settings: Settings, provider_name: str) -> None:
        self._settings = settings
        self._provider_name = provider_name

    def _feed_url(self, query: str | None) -> str:
        if self._provider_name == "google_news_rss":
            if query:
                return (
                    "https://news.google.com/rss/search?"
                    f"q={quote_plus(query)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
                )
            return "https://news.google.com/rss?hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        # Bing News RSS is more accessible from mainland networks than Google.
        effective_query = query or "今日热点"
        return (
            "https://www.bing.com/news/search?"
            f"q={quote_plus(effective_query)}&format=rss&setmkt=zh-CN&setlang=zh-cn"
        )

    async def _fetch_feed(self, query: str | None) -> list[SearchResultItem]:
        url = self._feed_url(query)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/131 Safari/537.36 goodnews/0.1"
            ),
            "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.5",
        }
        async with httpx.AsyncClient(
            timeout=self._settings.search_timeout_seconds,
            follow_redirects=True,
            headers=headers,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        root = ET.fromstring(response.text)
        items: list[SearchResultItem] = []
        for index, node in enumerate(root.iter()):
            if _local_name(node.tag) != "item":
                continue
            title = _clean_text(_child_text(node, "title"))
            link = _child_text(node, "link").strip()
            description = _clean_text(
                _child_text(node, "description") or _child_text(node, "encoded")
            )
            source_name = _clean_text(_child_text(node, "source"))
            published_at = _clean_text(_child_text(node, "pubdate")) or None
            if not title or not link:
                continue
            if not source_name and " - " in title:
                title, source_name = title.rsplit(" - ", 1)
            items.append(
                SearchResultItem(
                    id=_stable_id(link),
                    title=title,
                    url=link,
                    snippet=description[:600],
                    source_name=source_name or "未知来源",
                    published_at=published_at,
                    provider=self._provider_name,
                    rank=len(items) + 1,
                )
            )
            if len(items) >= self._settings.search_result_limit:
                break
        return items

    async def search(self, query: str, limit: int) -> list[SearchResultItem]:
        items = await self._fetch_feed(query)
        return items[:limit]

    async def hot(self, limit: int) -> list[SearchResultItem]:
        items = await self._fetch_feed(None)
        return items[:limit]


class SearchService:
    """Caching facade with provider failover."""

    def __init__(self, settings: Settings, cache: RedisCache) -> None:
        self._settings = settings
        self._cache = cache
        provider_order = [settings.search_provider]
        fallback = (
            "bing_rss"
            if settings.search_provider == "google_news_rss"
            else "google_news_rss"
        )
        provider_order.append(fallback)
        self._providers = [
            RSSNewsProvider(settings, name) for name in dict.fromkeys(provider_order)
        ]
        self.provider_name = settings.search_provider

    async def _search_with_failover(
        self, query: str, limit: int, hot: bool
    ) -> tuple[list[SearchResultItem], str, str | None]:
        last_error = ""
        for provider in self._providers:
            try:
                items = await (
                    provider.hot(limit) if hot else provider.search(query, limit)
                )
                if items:
                    return items, provider._provider_name, None
                last_error = "empty feed"
            except Exception as exc:  # noqa: BLE001 - public feeds are unreliable
                last_error = str(exc)
                logger.warning("RSS provider %s failed: %s", provider._provider_name, exc)
        return [], self.provider_name, last_error or "empty feed"

    async def _resolve_google_urls(
        self, items: list[SearchResultItem]
    ) -> list[SearchResultItem]:
        """Unwrap Google News redirect URLs to publisher URLs.

        Google News RSS returns internal ``/rss/articles/...`` links that serve
        a JS shell, not the article. The decoder uses Google's own public
        batchexecute endpoint. Failure is non-fatal: the original URL is kept
        and fact-check evidence can still fall back to the RSS snippet.
        """
        google_items = [
            item
            for item in items
            if (urlsplit(item.url).hostname or "").lower() == "news.google.com"
        ]
        if not google_items:
            return items

        try:
            async with GoogleDecoderAsync(timeout=self._settings.search_timeout_seconds) as decoder:
                decoded = await decoder.decode_google_news_urls(
                    [item.url for item in google_items],
                    concurrency=6,
                )
            by_original = {
                item.url: result.get("decoded_url")
                for item, result in zip(google_items, decoded, strict=False)
                if result.get("success") and result.get("decoded_url")
            }
            if by_original:
                return [
                    item.model_copy(update={"url": by_original.get(item.url, item.url)})
                    for item in items
                ]
        except Exception as exc:  # noqa: BLE001 - Google may change the endpoint
            logger.warning("Google News URL decode failed: %s", exc)
        return items

    async def search(self, query: str, limit: int | None = None) -> SearchResponse:
        limit = limit or self._settings.search_result_limit
        cache_key = f"goodnews:search:v2:{self.provider_name}:{limit}:{query}"
        cached = await self._cache.get_json(cache_key)
        if cached:
            try:
                parsed = SearchResponse.model_validate(cached)
                return parsed.model_copy(update={"cached": True})
            except ValueError:
                logger.debug("Ignoring malformed search cache entry")

        items, used_provider, last_error = await self._search_with_failover(
            query, limit, hot=False
        )
        items = await self._resolve_google_urls(items)
        error = None if items else f"新闻搜索服务暂时不可用：{last_error}"

        response = SearchResponse(
            query=query,
            items=items,
            provider=used_provider,
            fetched_at=datetime.now(UTC),
            error=error,
        )
        if items:
            await self._cache.set_json(cache_key, response.model_dump(mode="json"))
        return response

    async def hot(self, limit: int = 10, region: str = "CN") -> HotNewsResponse:
        cache_key = f"goodnews:hot:v2:{self.provider_name}:{region}:{limit}"
        cached = await self._cache.get_json(cache_key)
        if cached:
            try:
                return HotNewsResponse.model_validate(cached).model_copy(update={"cached": True})
            except ValueError:
                logger.debug("Ignoring malformed hot-news cache entry")

        items, used_provider, last_error = await self._search_with_failover("", limit, hot=True)
        items = await self._resolve_google_urls(items)
        error = None if items else f"热点暂时无法加载：{last_error}"

        response = HotNewsResponse(
            region=region,
            items=items,
            provider=used_provider,
            fetched_at=datetime.now(UTC),
            error=error,
        )
        if items:
            await self._cache.set_json(cache_key, response.model_dump(mode="json"))
        return response
