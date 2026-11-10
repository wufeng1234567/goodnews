"""Async facade that runs the Scrapy child process and normalizes its output."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Any

from app.core.config import BACKEND_ROOT, Settings
from app.models.article import ArticleContent

logger = logging.getLogger(__name__)


class ArticleFetchError(RuntimeError):
    """Raised when neither static nor Playwright extraction succeeds."""


class ScrapyArticleFetcher:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def _run_crawler(self, url: str, use_playwright: bool) -> dict[str, Any]:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as handle:
            output_path = Path(handle.name)

        command = [
            sys.executable,
            "-m",
            "app.crawler.runner",
            "--url",
            url,
            "--output",
            str(output_path),
            "--timeout-ms",
            str(self._settings.playwright_timeout_ms),
        ]
        if use_playwright:
            command.append("--playwright")
            if self._settings.playwright_browser_channel:
                command.extend(
                    ["--browser-channel", self._settings.playwright_browser_channel]
                )

        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(BACKEND_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self._settings.crawler_timeout_seconds
            )
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise ArticleFetchError("抓取超时，请换一个公开可访问的链接") from exc
        finally:
            # The child writes its own result; this read happens below.
            pass

        try:
            raw = output_path.read_text(encoding="utf-8")
            payload = json.loads(raw) if raw.strip() else {"ok": False, "error": "爬虫无输出"}
        except (OSError, json.JSONDecodeError) as exc:
            stderr_text = stderr.decode("utf-8", errors="replace")[-800:] if stderr else ""
            logger.warning("Crawler output unreadable: %s; stderr=%s", exc, stderr_text)
            raise ArticleFetchError("爬虫结果解析失败") from exc
        finally:
            output_path.unlink(missing_ok=True)

        if not payload.get("ok"):
            raise ArticleFetchError(str(payload.get("error") or "正文抓取失败"))
        return payload

    async def fetch(self, url: str) -> ArticleContent:
        """Try static Scrapy first, then Playwright if the body looks JS-rendered."""
        static_payload: dict[str, Any] | None = None
        static_error: Exception | None = None
        try:
            static_payload = await self._run_crawler(url, use_playwright=False)
            article = static_payload["article"]
            if len(article.get("text", "")) >= 200:
                return self._to_model(article, "scrapy")
        except ArticleFetchError as exc:
            static_error = exc

        if self._settings.crawler_playwright_enabled:
            try:
                rendered_payload = await self._run_crawler(url, use_playwright=True)
                return self._to_model(rendered_payload["article"], "scrapy_playwright")
            except ArticleFetchError as playwright_error:
                if static_error:
                    raise ArticleFetchError(
                        f"静态抓取失败（{static_error}）；浏览器渲染也失败（{playwright_error}）"
                    ) from playwright_error
                raise

        if static_payload is not None:
            # Short but valid static extraction is better than no result.
            return self._to_model(static_payload["article"], "scrapy")
        raise ArticleFetchError(str(static_error or "正文抓取失败"))

    @staticmethod
    def _to_model(article: dict[str, Any], fetched_with: str) -> ArticleContent:
        return ArticleContent(
            title=str(article.get("title") or "未命名文章"),
            url=str(article.get("url") or ""),
            text=str(article.get("text") or ""),
            author=article.get("author"),
            published_at=article.get("published_at"),
            source_name=article.get("source_name"),
            fetched_with=fetched_with,
            word_count=len(str(article.get("text") or "")),
        )
