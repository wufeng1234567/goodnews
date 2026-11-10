"""Resolve URL/text input into a normalized ArticleContent."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from app.core.config import Settings
from app.core.url_guard import assert_public_http_url
from app.crawler.service import ScrapyArticleFetcher
from app.models.article import ArticleContent
from app.models.common import InputType
from app.models.factcheck import FactCheckRequest


class ArticleService:
    def __init__(self, settings: Settings, fetcher: ScrapyArticleFetcher) -> None:
        self._settings = settings
        self._fetcher = fetcher

    @staticmethod
    def _is_probable_url(value: str) -> bool:
        if "\n" in value or " " in value.strip():
            return False
        parsed = urlsplit(value.strip())
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname)

    async def resolve(self, request: FactCheckRequest) -> ArticleContent:
        input_type = request.input_type
        is_url = input_type is InputType.URL or (
            input_type is InputType.AUTO and self._is_probable_url(request.content)
        )

        if is_url:
            url = await assert_public_http_url(request.content.strip())
            return await self._fetcher.fetch(url)

        text = request.content.strip()[: self._settings.max_article_chars]
        first_line = text.splitlines()[0].strip() if text.splitlines() else ""
        title = first_line[:120] if 2 <= len(first_line) <= 120 else "用户输入文本"
        # Basic cleanup: collapse spaces but preserve paragraph breaks.
        cleaned = re.sub(r"[ \t]+", " ", text).strip()
        return ArticleContent(
            title=title,
            url=None,
            text=cleaned,
            source_name="用户输入",
            fetched_with="input_text",
            word_count=len(cleaned),
        )
