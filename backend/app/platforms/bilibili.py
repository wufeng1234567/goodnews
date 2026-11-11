"""Bilibili adapter using public web APIs (no browser required)."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx

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
    PlatformContentNotFound,
    PlatformFetchError,
    count_comment_tree,
    parse_count,
    resolve_short_url,
    timestamp_to_datetime,
)
from app.platforms.browser import cookie_header

logger = logging.getLogger(__name__)

_BV_RE = re.compile(r"(BV[0-9A-Za-z]{10})")
_AV_RE = re.compile(r"(?:/video/av|^av)(\d+)", re.IGNORECASE)


class BilibiliAdapter:
    platform = SocialPlatform.BILIBILI

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def can_handle(self, url: str) -> bool:
        return any(host in url for host in ("bilibili.com", "b23.tv"))

    @staticmethod
    def extract_video_id(url: str) -> str:
        bv_match = _BV_RE.search(url)
        if bv_match:
            return bv_match.group(1)
        av_match = _AV_RE.search(url)
        if av_match:
            return f"av{av_match.group(1)}"
        raise PlatformContentNotFound(
            "无法从链接中识别 Bilibili BV/av 视频 ID",
            platform=SocialPlatform.BILIBILI,
        )

    def _headers(self) -> dict[str, str]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/131 Safari/537.36"
            ),
            "Referer": "https://www.bilibili.com/",
            "Accept": "application/json, text/plain, */*",
        }
        cookie = cookie_header(self._settings, SocialPlatform.BILIBILI)
        if cookie:
            headers["Cookie"] = cookie
        return headers

    async def _get_json(
        self, client: httpx.AsyncClient, path: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        response = await client.get(path, params=params)
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise PlatformFetchError(
                f"Bilibili API 错误 {payload.get('code')}: {payload.get('message') or '未知错误'}",
                platform=self.platform,
            )
        data = payload.get("data")
        return data if isinstance(data, dict) else {}

    async def fetch(self, request: SocialFetchRequest) -> SocialFetchResponse:
        final_url = await resolve_short_url(request.url)
        video_id = self.extract_video_id(final_url)

        async with httpx.AsyncClient(
            headers=self._headers(),
            timeout=25,
            follow_redirects=True,
        ) as client:
            view_params = {"bvid": video_id} if video_id.startswith("BV") else {"aid": video_id[2:]}
            try:
                video = await self._get_json(
                    client, "https://api.bilibili.com/x/web-interface/view", view_params
                )
            except (httpx.HTTPError, PlatformFetchError) as exc:
                raise PlatformFetchError(
                    f"无法获取 Bilibili 视频信息: {exc}",
                    platform=self.platform,
                    hint="确认视频公开可访问，且链接未失效",
                ) from exc

            content = parse_bilibili_video(video)
            comments: list[SocialComment] = []
            warnings: list[str] = []
            has_more = False
            try:
                comments, has_more = await self._fetch_comments(
                    client,
                    int(video["aid"]),
                    request.max_comments,
                    request.include_replies,
                )
            except (httpx.HTTPError, PlatformFetchError, KeyError) as exc:
                logger.warning("Bilibili comments failed: %s", exc)
                warnings.append(f"评论获取失败：{exc}")

            effective_max = request.max_comments or 50_000
            declared_comments = content.metrics.comment_count or 0
            if declared_comments > len(comments) and len(comments) < effective_max:
                warnings.append(
                    f"Bilibili 本次返回 {len(comments)} 条主评论"
                    f"（平台显示共 {declared_comments} 条）；配置 BILIBILI_COOKIE 可能提升完整度。"
                )

        return SocialFetchResponse(
            platform=self.platform,
            content=content,
            comments=comments,
            total_comments_fetched=count_comment_tree(comments),
            has_more=has_more,
            collection_method="public_api",
            auth_mode="cookie" if cookie_header(self._settings, SocialPlatform.BILIBILI) else "none",
            warnings=warnings,
        )

    async def _fetch_comments(
        self,
        client: httpx.AsyncClient,
        aid: int,
        max_comments: int,
        include_replies: bool,
    ) -> tuple[list[SocialComment], bool]:
        """Fetch top-level comments and, when requested, all nested replies.

        Bilibili's ``/x/v2/reply/reply`` endpoint is a separate paginated API
        for each root comment. The legacy top-level response only includes the
        first 3 nested replies, which is why the UI previously looked truncated.
        """
        target = max_comments or 50_000
        # Keep a quick preview useful: a single viral comment can have
        # hundreds of replies. Full jobs (target > 200) fetch every reply.
        nested_cap = 5 if max_comments and max_comments <= 200 else None
        comments: list[SocialComment] = []
        page_number = 1
        total_count = 0
        page_size = 20
        while count_comment_tree(comments) < target:
            data = await self._get_json(
                client,
                "https://api.bilibili.com/x/v2/reply",
                {
                    "type": 1,
                    "oid": aid,
                    "pn": page_number,
                    "ps": page_size,
                    "sort": 2,
                },
            )
            page = data.get("page") or {}
            total_count = parse_count(page.get("count"))
            replies = data.get("replies") or []
            if not replies:
                break
            for raw in replies:
                if count_comment_tree(comments) >= target:
                    break
                comment = parse_bilibili_comment(raw, content_id=str(aid))
                reply_count = parse_count(raw.get("rcount") or raw.get("count"))
                if include_replies and reply_count:
                    remaining = target - count_comment_tree(comments) - 1
                    if nested_cap is not None:
                        remaining = min(remaining, nested_cap)
                    if remaining > 0:
                        sub_comments = await self._fetch_sub_replies(
                            client, aid, comment.id, remaining
                        )
                        comment = comment.model_copy(update={"replies": sub_comments})
                comments.append(comment)
            if len(replies) < page_size:
                break
            page_number += 1
            await asyncio.sleep(0.15)

        return comments, total_count > len(comments)

    async def fetch_root_replies(
        self,
        *,
        content_id: str,
        root_id: str,
        max_comments: int = 50_000,
    ) -> list[SocialComment]:
        """Fetch the complete reply tree for one Bilibili root comment."""
        video_id = self.extract_video_id(content_id)
        async with httpx.AsyncClient(
            headers=self._headers(),
            timeout=25,
            follow_redirects=True,
        ) as client:
            view_params = {"bvid": video_id} if video_id.startswith("BV") else {"aid": video_id[2:]}
            video = await self._get_json(
                client, "https://api.bilibili.com/x/web-interface/view", view_params
            )
            return await self._fetch_sub_replies(
                client,
                int(video["aid"]),
                root_id,
                max_comments,
            )

    async def _fetch_sub_replies(
        self,
        client: httpx.AsyncClient,
        aid: int,
        root_id: str,
        limit: int,
    ) -> list[SocialComment]:
        """Fetch all pages of replies for one root comment."""
        out: list[SocialComment] = []
        page_number = 1
        page_size = 20
        while len(out) < limit:
            data = await self._get_json(
                client,
                "https://api.bilibili.com/x/v2/reply/reply",
                {
                    "type": 1,
                    "oid": aid,
                    "root": root_id,
                    "pn": page_number,
                    "ps": page_size,
                    "sort": 2,
                },
            )
            page = data.get("page") or {}
            total = parse_count(page.get("count"))
            replies = data.get("replies") or []
            if not replies:
                break
            for raw in replies:
                if len(out) >= limit:
                    break
                out.append(
                    parse_bilibili_comment(
                        raw,
                        content_id=str(aid),
                        parent_id=root_id,
                    )
                )
            if len(replies) < page_size or len(out) >= total:
                break
            page_number += 1
            await asyncio.sleep(0.12)
        return out


def parse_bilibili_video(data: dict[str, Any]) -> SocialContent:
    stat = data.get("stat") or {}
    owner = data.get("owner") or {}
    bvid = str(data.get("bvid") or "")
    aid = str(data.get("aid") or "")
    pubdate = timestamp_to_datetime(data.get("pubdate"))
    return SocialContent(
        platform=SocialPlatform.BILIBILI,
        content_id=bvid or aid,
        content_type=SocialContentType.VIDEO,
        url=f"https://www.bilibili.com/video/{bvid or ('av' + aid)}",
        title=str(data.get("title") or "未命名视频"),
        description=str(data.get("desc") or ""),
        author=SocialAuthor(
            id=str(owner.get("mid") or ""),
            name=str(owner.get("name") or "未知UP主"),
            profile_url=f"https://space.bilibili.com/{owner.get('mid')}"
            if owner.get("mid")
            else None,
            avatar_url=owner.get("face"),
        ),
        published_at=pubdate,
        cover_url=data.get("pic"),
        duration_seconds=_parse_duration(data.get("duration")),
        tags=[str(data["tname"])] if data.get("tname") else [],
        metrics=SocialMetrics(
            view_count=parse_count(stat.get("view")),
            play_count=parse_count(stat.get("vv")) or None,
            like_count=parse_count(stat.get("like")),
            comment_count=parse_count(stat.get("reply")),
            share_count=parse_count(stat.get("share")),
            collect_count=parse_count(stat.get("favorite")),
            coin_count=parse_count(stat.get("coin")),
            danmaku_count=parse_count(stat.get("danmaku")),
        ),
    )


def _parse_duration(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if ":" in text:
        total = 0
        for part in text.split(":"):
            total = total * 60 + parse_count(part)
        return total
    return parse_count(text) or None


def parse_bilibili_comment(
    data: dict[str, Any],
    *,
    content_id: str,
    parent_id: str | None = None,
) -> SocialComment:
    member = data.get("member") or {}
    content = data.get("content") or {}
    likes = parse_count(data.get("like"))
    return SocialComment(
        id=str(data.get("rpid_str") or data.get("rpid") or ""),
        content_id=content_id,
        parent_id=parent_id,
        text=str(content.get("message") or ""),
        author_name=str(member.get("uname") or "匿名用户"),
        author_id=str(member.get("mid") or ""),
        author_avatar_url=member.get("avatar"),
        like_count=likes,
        reply_count=parse_count(data.get("rcount") or data.get("count")),
        created_at=timestamp_to_datetime(data.get("ctime")),
        replies=[],
    )
