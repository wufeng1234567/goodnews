"""Xiaohongshu adapter with login-state-aware browser extraction.

XHS aggressively challenges anonymous browser sessions. The adapter never
pretends anonymous success: if the page lands on a login/security wall, it
returns a structured auth-required error telling the user how to save a local
login state. With that state, note details and comment JSON are captured from
the page's own API traffic.
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
    find_first_dict,
    parse_count,
    timestamp_to_datetime,
)
from app.platforms.browser import (
    auth_mode,
    login_required_message,
    open_browser_page,
)

logger = logging.getLogger(__name__)

_NOTE_PATTERNS = [
    re.compile(r"/explore/([0-9a-zA-Z]+)"),
    re.compile(r"/discovery/item/([0-9a-zA-Z]+)"),
]
_FEED_ENDPOINT = "/api/sns/web/v1/feed"
_COMMENT_ENDPOINTS = ("/api/sns/web/v2/comment/page", "/api/sns/web/v1/comment/page")


class XiaohongshuAdapter:
    platform = SocialPlatform.XIAOHONGSHU

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def can_handle(self, url: str) -> bool:
        return any(host in url for host in ("xiaohongshu.com", "xhslink.com"))

    @staticmethod
    def extract_note_id(url: str) -> str | None:
        for pattern in _NOTE_PATTERNS:
            match = pattern.search(url)
            if match:
                return match.group(1)
        return None

    async def fetch(self, request: SocialFetchRequest) -> SocialFetchResponse:
        note_payloads: list[dict[str, Any]] = []
        comment_payloads: list[dict[str, Any]] = []
        page_url = request.url
        page_text = ""

        async with open_browser_page(self._settings, self.platform) as page:
            capture_tasks: set[asyncio.Task] = set()

            async def capture_response(response) -> None:
                try:
                    if _FEED_ENDPOINT in response.url:
                        payload = await response.json()
                        if isinstance(payload, dict):
                            note_payloads.append(payload)
                    elif any(path in response.url for path in _COMMENT_ENDPOINTS):
                        payload = await response.json()
                        if isinstance(payload, dict):
                            comment_payloads.append(payload)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("XHS response parse skipped: %s", exc)

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
                logger.warning("XHS page load timed out; trying any captured data")

            await page.wait_for_timeout(4_000)
            page_url = page.url
            try:
                page_text = await page.locator("body").inner_text(timeout=4_000)
            except Exception:  # noqa: BLE001
                page_text = ""

            if self._looks_like_auth_wall(page_url, page_text):
                raise PlatformAuthRequired(
                    login_required_message(self.platform),
                    platform=self.platform,
                    hint=rf"运行 scripts\social-login.bat {self.platform.value}",
                )

            try:
                await page.keyboard.press("Escape")
            except Exception as exc:  # noqa: BLE001
                logger.debug("XHS login overlay dismissal skipped: %s", exc)

            # XHS lazy-loads comments as the note panel is scrolled.
            target_comments = request.max_comments or 50_000
            max_loops = 14 if target_comments <= 100 else min(500, 14 + target_comments // 5)
            for _ in range(max_loops):
                await page.mouse.wheel(0, 900)
                await page.wait_for_timeout(800)
                loaded = sum(
                    len(item.get("data", {}).get("comments", []))
                    for item in comment_payloads
                )
                if loaded >= target_comments:
                    break

            if capture_tasks:
                await asyncio.gather(*capture_tasks, return_exceptions=True)

            note_data = self._extract_note_payload(note_payloads)
            if note_data is None:
                dom_data = await self._extract_dom_note(page)
                if dom_data:
                    content = parse_xhs_dom_content(dom_data, page_url)
                    comments = parse_xhs_dom_comments(dom_data.get("comments", []), content.content_id)
                    return SocialFetchResponse(
                        platform=self.platform,
                        content=content,
                        comments=comments[: request.max_comments],
                        total_comments_fetched=min(
                            count_comment_tree(comments), request.max_comments
                        ),
                        has_more=len(comments) > request.max_comments,
                        collection_method="browser_dom",
                        auth_mode=auth_mode(self._settings, self.platform),
                        warnings=["使用页面 DOM 兜底解析，评论数可能少于实际值。"],
                    )
                raise PlatformContentNotFound(
                    "没有从页面中解析到小红书笔记内容",
                    platform=self.platform,
                    hint="确认笔记公开可访问，并运行小红书登录辅助脚本",
                )

        content = parse_xhs_content(note_data, source_url=page_url)
        comments, has_more = parse_xhs_comments(
            comment_payloads,
            content_id=content.content_id,
            max_comments=request.max_comments,
        )
        warnings: list[str] = []
        declared_comments = content.metrics.comment_count or 0
        if not comments and declared_comments:
            warnings.append("已获取笔记，但评论接口未返回数据；可尝试重新登录后重试。")
        if has_more:
            warnings.append("评论区还有更多内容，当前已按数量上限截断。")

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

    @staticmethod
    def _looks_like_auth_wall(page_url: str, page_text: str) -> bool:
        markers = (
            "当前笔记暂时无法浏览",
            "当前网络存在风险",
            "请登录",
            "登录后查看",
            "安全验证",
            "website-login/error",
        )
        return any(marker in page_url for marker in markers) or any(
            marker in page_text for marker in markers
        )

    @staticmethod
    def _extract_note_payload(payloads: list[dict[str, Any]]) -> dict[str, Any] | None:
        for payload in payloads:
            data = payload.get("data")
            if isinstance(data, dict):
                items = data.get("items")
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and isinstance(item.get("note_card"), dict):
                            return item["note_card"]
                note = data.get("note")
                if isinstance(note, dict):
                    return note
            found = find_first_dict(
                payload,
                lambda value: "note_id" in value
                and any(key in value for key in ("display_title", "title", "desc")),
            )
            if found:
                return found
        return None

    @staticmethod
    async def _extract_dom_note(page) -> dict[str, Any] | None:
        try:
            data = await page.evaluate(
                """
                () => {
                  const text = (selector) => {
                    const node = document.querySelector(selector);
                    return node ? (node.innerText || node.textContent || '').trim() : '';
                  };
                  const attr = (selector, name) => {
                    const node = document.querySelector(selector);
                    return node ? node.getAttribute(name) : '';
                  };
                  const comments = Array.from(document.querySelectorAll('.comment-item')).slice(0, 50).map((node, index) => ({
                    id: node.getAttribute('data-id') || `dom-${index}`,
                    text: (node.querySelector('.content .note-text, .note-text, .content')?.innerText || '').trim(),
                    author: (node.querySelector('.author .name, .name')?.innerText || '').trim(),
                    likes: (node.querySelector('.like .count, .count')?.innerText || '0').trim(),
                  }));
                  return {
                    title: text('#detail-title') || text('.note-content .title') || text('h1'),
                    description: text('#detail-desc') || text('.note-content .desc') || text('.note-text'),
                    author: text('.author-wrapper .name') || text('.author .name') || text('.username'),
                    likes: text('.interact-container .like-wrapper .count') || text('.like-wrapper .count'),
                    collects: text('.interact-container .collect-wrapper .count') || text('.collect-wrapper .count'),
                    comments_count: text('.interact-container .chat-wrapper .count') || text('.chat-wrapper .count'),
                    cover: attr('meta[property="og:image"]', 'content') || attr('.media-container img', 'src'),
                    comments,
                  };
                }
                """
            )
            if isinstance(data, dict) and (data.get("title") or data.get("description")):
                return data
        except Exception as exc:  # noqa: BLE001
            logger.debug("XHS DOM fallback failed: %s", exc)
        return None


def parse_xhs_content(note: dict[str, Any], source_url: str | None = None) -> SocialContent:
    note_id = str(note.get("note_id") or note.get("id") or "")
    user = note.get("user") or {}
    interact = note.get("interact_info") or note.get("interact") or {}
    desc = str(note.get("desc") or "")
    first_line = next((line.strip() for line in desc.splitlines() if line.strip()), "")
    title = str(note.get("display_title") or note.get("title") or first_line or "未命名笔记").strip()
    note_type = str(note.get("type") or "normal")
    media_urls = _xhs_media_urls(note)
    cover = media_urls[0] if media_urls else None
    tags = [
        str(tag.get("name"))
        for tag in (note.get("tag_list") or [])
        if isinstance(tag, dict) and tag.get("name")
    ]
    published = timestamp_to_datetime(
        note.get("time") or note.get("last_update_time") or note.get("create_time")
    )
    return SocialContent(
        platform=SocialPlatform.XIAOHONGSHU,
        content_id=note_id,
        content_type=SocialContentType.VIDEO
        if note_type == "video"
        else SocialContentType.NOTE,
        url=source_url or f"https://www.xiaohongshu.com/explore/{note_id}",
        title=title[:300],
        description=desc,
        author=SocialAuthor(
            id=str(user.get("user_id") or user.get("id") or ""),
            name=str(user.get("nickname") or user.get("name") or "未知作者"),
            avatar_url=user.get("avatar") or user.get("image"),
            profile_url=f"https://www.xiaohongshu.com/user/profile/{user.get('user_id')}"
            if user.get("user_id")
            else None,
        ),
        published_at=published,
        cover_url=cover,
        media_urls=media_urls,
        tags=tags,
        metrics=SocialMetrics(
            like_count=parse_count(interact.get("liked_count") or interact.get("like_count")),
            comment_count=parse_count(
                interact.get("comment_count") or interact.get("comments_count")
            ),
            share_count=parse_count(interact.get("share_count")),
            collect_count=parse_count(
                interact.get("collected_count") or interact.get("collect_count")
            ),
        ),
    )


def parse_xhs_comments(
    pages: list[dict[str, Any]],
    *,
    content_id: str,
    max_comments: int,
) -> tuple[list[SocialComment], bool]:
    comments: list[SocialComment] = []
    seen: set[str] = set()
    has_more = False
    for page in pages:
        data = page.get("data") or {}
        has_more = has_more or bool(data.get("has_more"))
        raw_comments = data.get("comments") or []
        for raw in raw_comments:
            if len(comments) >= max_comments:
                break
            comment = _parse_xhs_comment(raw, content_id=content_id)
            if comment.id and comment.id not in seen:
                seen.add(comment.id)
                comments.append(comment)
            for sub in raw.get("sub_comments") or []:
                if len(comments) >= max_comments:
                    break
                reply = _parse_xhs_comment(sub, content_id=content_id, parent_id=comment.id)
                if reply.id and reply.id not in seen:
                    seen.add(reply.id)
                    comment.replies.append(reply)
    return comments, has_more


def _parse_xhs_comment(
    raw: dict[str, Any],
    *,
    content_id: str,
    parent_id: str | None = None,
) -> SocialComment:
    user = raw.get("user_info") or raw.get("user") or {}
    return SocialComment(
        id=str(raw.get("id") or raw.get("comment_id") or ""),
        content_id=content_id,
        parent_id=parent_id,
        text=str(raw.get("content") or ""),
        author_name=str(user.get("nickname") or "匿名用户"),
        author_id=str(user.get("user_id") or user.get("id") or ""),
        author_avatar_url=user.get("image") or user.get("avatar"),
        like_count=parse_count(raw.get("like_count")),
        reply_count=parse_count(raw.get("sub_comment_count") or raw.get("reply_count")),
        created_at=timestamp_to_datetime(raw.get("create_time")),
        replies=[],
    )


def parse_xhs_dom_content(data: dict[str, Any], page_url: str) -> SocialContent:
    note_id = XiaohongshuAdapter.extract_note_id(page_url) or ""
    return SocialContent(
        platform=SocialPlatform.XIAOHONGSHU,
        content_id=note_id,
        content_type=SocialContentType.NOTE,
        url=page_url,
        title=str(data.get("title") or "未命名笔记")[:300],
        description=str(data.get("description") or ""),
        author=SocialAuthor(name=str(data.get("author") or "未知作者")),
        cover_url=str(data.get("cover") or "") or None,
        metrics=SocialMetrics(
            like_count=parse_count(data.get("likes")),
            collect_count=parse_count(data.get("collects")),
            comment_count=parse_count(data.get("comments_count")),
        ),
    )


def parse_xhs_dom_comments(
    raw_comments: list[dict[str, Any]], content_id: str
) -> list[SocialComment]:
    return [
        SocialComment(
            id=str(item.get("id") or f"dom-{index}"),
            content_id=content_id,
            text=str(item.get("text") or ""),
            author_name=str(item.get("author") or "匿名用户"),
            like_count=parse_count(item.get("likes")),
        )
        for index, item in enumerate(raw_comments)
        if item.get("text")
    ]


def _xhs_media_urls(note: dict[str, Any]) -> list[str]:
    """Collect all image URLs for an image note; videos expose their cover."""
    images = note.get("image_list") or note.get("images") or []
    urls: list[str] = []
    for image in images:
        if not isinstance(image, dict):
            continue
        url = (
            image.get("url_default")
            or image.get("url")
            or image.get("url_pre")
            or _first_nested_url(image.get("info_list"))
        )
        if url and url not in urls:
            urls.append(str(url))
    if not urls:
        video = note.get("video") or {}
        cover = video.get("cover") or video.get("image") or {}
        if isinstance(cover, dict):
            url = (
                cover.get("url_default")
                or cover.get("url")
                or _first_nested_url(cover.get("url_list"))
            )
            if url:
                urls.append(str(url))
    return urls


def _first_nested_url(value: Any) -> str | None:
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict):
            return first.get("url") or first.get("url_default")
    return None
