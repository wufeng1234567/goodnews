"""Turn search hits into traceable evidence records."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any

from app.core.config import Settings
from app.core.url_guard import URLGuardError, assert_public_http_url
from app.crawler.service import ArticleFetchError, ScrapyArticleFetcher
from app.models.factcheck import Claim, Evidence
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)


def _evidence_id(url: str) -> str:
    return "ev-" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]


def _claim_ids_for_query(query: str, claims: list[Claim]) -> list[str]:
    """Associate a query with the claim it was derived from.

    The node derives initial queries from claim text and follow-up queries add
    a suffix such as “官方 回应”. A prefix match is deliberately conservative;
    when no claim matches, the hit is attached to all claims as background.
    """
    normalized_query = query.replace(" ", "")
    matched = [
        claim.id
        for claim in claims
        if claim.text.replace(" ", "")[:36] in normalized_query
    ]
    return matched or [claim.id for claim in claims]


class EvidenceService:
    def __init__(
        self,
        settings: Settings,
        search: SearchService,
        fetcher: ScrapyArticleFetcher,
    ) -> None:
        self._settings = settings
        self._search = search
        self._fetcher = fetcher

    async def _search_one(self, query: str, limit: int) -> tuple[str, list[Any]]:
        response = await self._search.search(query, limit=limit)
        # Search errors are surfaced as an empty list; evidence insufficiency
        # is a valid graph state, not an API failure.
        return query, response.items

    async def _enrich(self, item: Evidence) -> Evidence:
        """Fetch full text for top hits; silently fall back to RSS snippet."""
        try:
            await assert_public_http_url(item.url)
            article = await self._fetcher.fetch(item.url)
            return item.model_copy(
                update={
                    "title": article.title or item.title,
                    "content_excerpt": article.text[:2_000],
                    "source_name": article.source_name or item.source_name,
                    "published_at": article.published_at or item.published_at,
                }
            )
        except (URLGuardError, ArticleFetchError) as exc:
            logger.info("Evidence enrichment skipped for %s: %s", item.url, exc)
            return item

    async def retrieve(
        self,
        claims: list[Claim],
        queries: list[str],
        existing: list[Evidence],
    ) -> list[Evidence]:
        if not claims or not queries:
            return []

        existing_urls = {item.url for item in existing}
        results = await asyncio.gather(
            *[self._search_one(query, limit=3) for query in queries[:4]],
            return_exceptions=True,
        )

        by_url: dict[str, Evidence] = {}
        for result in results:
            if isinstance(result, BaseException):
                logger.warning("Evidence search task failed: %s", result)
                continue
            query, items = result
            for item in items:
                if item.url in existing_urls:
                    continue
                claim_ids = _claim_ids_for_query(query, claims)
                existing_evidence = by_url.get(item.url)
                if existing_evidence is not None:
                    merged_ids = list(dict.fromkeys(existing_evidence.claim_ids + claim_ids))
                    by_url[item.url] = existing_evidence.model_copy(
                        update={"claim_ids": merged_ids}
                    )
                    continue
                by_url[item.url] = Evidence(
                    id=_evidence_id(item.url),
                    claim_ids=claim_ids,
                    title=item.title,
                    url=item.url,
                    snippet=item.snippet,
                    content_excerpt=item.snippet,
                    source_name=item.source_name,
                    published_at=item.published_at,
                    relevance=max(0.35, 0.8 - item.rank * 0.05),
                    query=query,
                )

        candidates = list(by_url.values())
        enrichment_targets = candidates[: self._settings.evidence_fetch_top_n]
        if enrichment_targets:
            enriched = await asyncio.gather(
                *[self._enrich(item) for item in enrichment_targets],
                return_exceptions=True,
            )
            for index, item in enumerate(enriched):
                if isinstance(item, BaseException):
                    logger.warning("Evidence enrichment task failed: %s", item)
                elif isinstance(item, Evidence):
                    candidates[index] = item

        return candidates[:12]
