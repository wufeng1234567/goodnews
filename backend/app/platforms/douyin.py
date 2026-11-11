"""Douyin adapter based on Playwright network responses.

Douyin signs its web APIs with browser-generated values. Rather than copying
fragile signature code, we open the public video page in the user's browser and
read the same JSON responses the page receives. Cookies are optional for many
public videos; a saved login state improves reliability and comment access.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.core.config import Settings
from app.models.social import (
    SocialAuthor,
    SocialComment,
    SocialContent,
    SocialContentType,
    SocialFetchRequest,
    SocialFetchResponse,
    SocialMetrics,
    SocialPlatform,
)
from app.platforms.base import (
    PlatformAuthRequired,
    PlatformContentNotFound,
    count_comment_tree,
    parse_count,
    timestamp_to_datetime,
)
from app.platforms.browser import (
    auth_mode,
    login_required_message,
    open_browser_page,
)

logger = logging.getLogger(__name__)

_ID_PATTERNS = [
    re.compile(r"/video/(\d+)"),
    re.compile(r"/note/(\d+)"),
    re.compile(r"modal_id=(\d+)"),
    re.compile(r"item_ids=(\d+)"),
]
_COMMENT_ENDPOINT = "/aweme/v1/web/comment/list/"
_DETAIL_ENDPOINT = "/aweme/v1/web/aweme/detail/"


class DouyinAdapter:
    platform = SocialPlatform.DOUYIN

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def can_handle(self, url: str) -> bool:
        return any(host in url for host in ("douyin.com", "iesdouyin.com"))

    @staticmethod
    def extract_content_id(url: str) -> str | None:
        for pattern in _ID_PATTERNS:
            match = pattern.search(url)
            if match:
                return match.group(1)
        return None

    async def fetch(self, request: SocialFetchRequest) -> SocialFetchResponse:
        detail: dict[str, Any] = {}
        comment_pages: list[dict[str, Any]] = []
        page_url = request.url
        page_title = ""
        page_text = ""
        content_id = self.extract_content_id(request.url)

        async with open_browser_page(self._settings, self.platform) as page:
            capture_tasks: set[asyncio.Task] = set()

            async def capture_response(response) -> None:
                try:
                    if _DETAIL_ENDPOINT in response.url:
                        payload = await response.json()
                        if isinstance(payload, dict) and payload.get("aweme_detail"):
                            detail.update(payload)
                    elif _COMMENT_ENDPOINT in response.url:
                        payload = await response.json()
                        if isinstance(payload, dict):
                            comment_pages.append(payload)
                except Exception as exc:  # noqa: BLE001 - a single bad response is non-fatal
                    logger.debug("Douyin response parse skipped: %s", exc)

            page.on(
                "response",
                lambda response: capture_tasks.add(asyncio.create_task(capture_response(response))),
            )

            try:
                await page.goto(
                    request.url,
                    wait_until="domcontentloaded",
                    timeout=self._settings.social_browser_timeout_ms,
                )
            except PlaywrightTimeoutError:
                logger.warning("Douyin page load timed out; using captured responses if any")

            await page.wait_for_timeout(3_000)
            page_url = page.url
            page_title = await page.title()
            try:
                page_text = await page.locator("body").inner_text(timeout=3_000)
            except Exception:  # noqa: BLE001
                page_text = ""
            content_id = content_id or self.extract_content_id(page_url)

            if not detail:
                for _ in range(12):
                    if detail:
                        break
                    await page.wait_for_timeout(500)

            if not detail:
                lowered = page_text.lower()
                if any(
                    marker in page_text
                    for marker in ("登录后", "安全验证", "验证码", "访问过于频繁")
                ) or "login" in lowered:
                    raise PlatformAuthRequired(
                        login_required_message(self.platform),
                        platform=self.platform,
                        hint=rf"运行 scripts\social-login.bat {self.platform.value}",
                    )
                raise PlatformContentNotFound(
                    f"未能获取抖音内容信息（页面标题：{page_title or '未知'}）",
                    platform=self.platform,
                    hint="确认视频仍公开，或运行登录辅助脚本后重试",
                )

            if not content_id:
                content_id = str((detail.get("aweme_detail") or {}).get("aweme_id") or "")

            # Closing the login overlay (when present) allows the page to load
            # comment rows. Many public videos expose comments without login.
            try:
                await page.keyboard.press("Escape")
            except Exception as exc:  # noqa: BLE001
                logger.debug("Douyin login overlay dismissal skipped: %s", exc)

            # The video page lazy-loads its comment panel. Move it into view and
            # scroll both the window and any virtualized inner list. This is the
            # step that triggers the page's own signed comment request.
            try:
                comment_label = page.get_by_text("全部评论", exact=True).first
                await comment_label.scroll_into_view_if_needed(timeout=5_000)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Douyin comment label not found: %s", exc)
            try:
                await page.mouse.move(900, 700)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Douyin mouse positioning skipped: %s", exc)

            previous_count = 0
            stagnant = 0
            for _ in range(12):
                await page.mouse.wheel(0, 1_000)
                await page.evaluate(
                    """() => {
                      window.scrollTo(0, document.body.scrollHeight);
                      const nodes = Array.from(document.querySelectorAll('*'))
                        .filter((node) => node.scrollHeight > node.clientHeight + 120)
                        .sort((a, b) => b.scrollHeight - a.scrollHeight)
                        .slice(0, 5);
                      for (const node of nodes) node.scrollTop = node.scrollHeight;
                    }"""
                )
                await page.wait_for_timeout(1_100)
                current_count = sum(
                    len(item.get("comments") or []) for item in comment_pages if isinstance(item, dict)
                )
                if current_count >= request.max_comments:
                    break
                if current_count == previous_count:
                    stagnant += 1
                    if stagnant >= 5:
                        break
                else:
                    stagnant = 0
                    previous_count = current_count
            await page.wait_for_timeout(1_500)

            if capture_tasks:
                await asyncio.gather(*capture_tasks, return_exceptions=True)

        aweme = detail.get("aweme_detail") or {}
        if not aweme or not content_id:
            raise PlatformContentNotFound(
                "抖音详情响应为空，可能被风控拦截",
                platform=self.platform,
            )

        content = parse_douyin_content(aweme)
        comments, has_more = parse_douyin_comments(
            comment_pages,
            content_id=content_id,
            max_comments=request.max_comments,
        )
        warnings: list[str] = []
        declared_comments = content.metrics.comment_count or 0
        if not comments and declared_comments:
            warnings.append(
                "页面未返回评论数据；可尝试运行 scripts\\social-login.bat douyin 后重试。"
            )
        elif has_more:
            warnings.append(
                f"平台当前已返回 {len(comments)} 条评论，仍有更多评论需要继续滚动加载。"
            )

        return SocialFetchResponse(
            platform=self.platform,
            content=content,
            comments=comments,
            total_comments_fetched=count_comment_tree(comments),
            has_more=has_more,
            collection_method="browser_api",
            auth_mode=auth_mode(self._settings, self.platform),
            warnings=warnings,
        )


def parse_douyin_content(aweme: dict[str, Any]) -> SocialContent:
    author = aweme.get("author") or {}
    statistics = aweme.get("statistics") or {}
    video = aweme.get("video") or {}
    cover = _first_url(video.get("cover") or video.get("origin_cover"))
    images = aweme.get("images") or []
    content_type = SocialContentType.NOTE if images else SocialContentType.VIDEO
    desc = str(aweme.get("desc") or "").strip()
    title = desc.splitlines()[0].strip() if desc else "未命名抖音内容"
    tags = [
        str(item.get("hashtag_name"))
        for item in (aweme.get("text_extra") or [])
        if item.get("hashtag_name")
    ]
    duration_ms = aweme.get("duration") or video.get("duration")
    play_count = parse_count(statistics.get("play_count"))
    extra = {
        key: parse_count(statistics.get(key))
        for key in ("recommend_count", "admire_count")
        if parse_count(statistics.get(key))
    }
    return SocialContent(
        platform=SocialPlatform.DOUYIN,
        content_id=str(aweme.get("aweme_id") or ""),
        content_type=content_type,
        url=f"https://www.douyin.com/video/{aweme.get('aweme_id')}",
        title=title[:300],
        description=desc,
        author=SocialAuthor(
            id=str(author.get("uid") or ""),
            name=str(author.get("nickname") or "未知作者"),
            handle=str(author.get("unique_id") or ""),
            avatar_url=_first_url(author.get("avatar_thumb")),
            profile_url=f"https://www.douyin.com/user/{author.get('sec_uid')}"
            if author.get("sec_uid")
            else None,
            follower_count=parse_count(author.get("follower_count")) or None,
        ),
        published_at=timestamp_to_datetime(aweme.get("create_time")),
        cover_url=cover,
        duration_seconds=int(duration_ms / 1000) if duration_ms else None,
        tags=tags,
        metrics=SocialMetrics(
            view_count=play_count or None,
            play_count=play_count or None,
            like_count=parse_count(statistics.get("digg_count")),
            comment_count=parse_count(statistics.get("comment_count")),
            share_count=parse_count(statistics.get("share_count")),
            collect_count=parse_count(statistics.get("collect_count")),
            extra=extra,
        ),
    )


def parse_douyin_comments(
    pages: list[dict[str, Any]],
    *,
    content_id: str,
    max_comments: int,
) -> tuple[list[SocialComment], bool]:
    comments: list[SocialComment] = []
    seen: set[str] = set()
    has_more = False
    for page in pages:
        has_more = has_more or bool(page.get("has_more"))
        for raw in page.get("comments") or []:
            if len(comments) >= max_comments:
                break
            comment = _parse_douyin_comment(raw, content_id=content_id)
            if comment.id and comment.id not in seen:
                seen.add(comment.id)
                comments.append(comment)
            for sub in raw.get("reply_comment") or []:
                if len(comments) >= max_comments:
                    break
                reply = _parse_douyin_comment(
                    sub, content_id=content_id, parent_id=comment.id
                )
                if reply.id and reply.id not in seen:
                    seen.add(reply.id)
                    comment.replies.append(reply)
        if len(comments) >= max_comments:
            break
    return comments, has_more or len(comments) >= max_comments


def _parse_douyin_comment(
    raw: dict[str, Any],
    *,
    content_id: str,
    parent_id: str | None = None,
) -> SocialComment:
    user = raw.get("user") or {}
    return SocialComment(
        id=str(raw.get("cid") or ""),
        content_id=content_id,
        parent_id=parent_id,
        text=str(raw.get("text") or ""),
        author_name=str(user.get("nickname") or "匿名用户"),
        author_id=str(user.get("uid") or ""),
        author_avatar_url=_first_url(user.get("avatar_thumb")),
        like_count=parse_count(raw.get("digg_count")),
        reply_count=parse_count(raw.get("reply_comment_total")),
        created_at=timestamp_to_datetime(raw.get("create_time")),
        replies=[],
    )


def _first_url(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    urls = value.get("url_list") or []
    return str(urls[0]) if urls else None
