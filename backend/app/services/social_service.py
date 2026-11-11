"""Social-platform ingestion orchestration."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import Settings
from app.db.social_repository import SocialFetchRepository
from app.models.social import (
    SocialFetchRequest,
    SocialFetchResponse,
    SocialPlatform,
    SocialPlatformInfo,
    SocialPlatformListResponse,
)
from app.platforms.base import (
    LOGIN_COMMANDS,
    PLATFORM_LABELS,
    PlatformDetectError,
    detect_platform,
    extract_first_url,
)
from app.platforms.bilibili import BilibiliAdapter
from app.platforms.douyin import DouyinAdapter
from app.platforms.xiaohongshu import XiaohongshuAdapter

logger = logging.getLogger(__name__)


class SocialService:
    def __init__(self, settings: Settings, repository: SocialFetchRepository) -> None:
        self._settings = settings
        self._repository = repository
        self._adapters: dict[SocialPlatform, Any] = {
            SocialPlatform.BILIBILI: BilibiliAdapter(settings),
            SocialPlatform.DOUYIN: DouyinAdapter(settings),
            SocialPlatform.XIAOHONGSHU: XiaohongshuAdapter(settings),
        }

    def platform_list(self) -> SocialPlatformListResponse:
        notes = {
            SocialPlatform.BILIBILI: "公开 API；支持视频详情、统计数据和评论。",
            SocialPlatform.DOUYIN: "浏览器采集；公开视频可读取详情与评论，登录态更稳定。",
            SocialPlatform.XIAOHONGSHU: "需要登录态；匿名访问会进入安全验证页。",
        }
        return SocialPlatformListResponse(
            platforms=[
                SocialPlatformInfo(
                    platform=platform,
                    label=PLATFORM_LABELS[platform],
                    supported=True,
                    needs_login_for_comments=platform is SocialPlatform.XIAOHONGSHU,
                    login_command=LOGIN_COMMANDS[platform],
                    note=notes[platform],
                )
                for platform in SocialPlatform
            ]
        )

    async def fetch(self, request: SocialFetchRequest) -> SocialFetchResponse:
        url = extract_first_url(request.url)
        platform = detect_platform(url)
        adapter = self._adapters.get(platform)
        if adapter is None or not adapter.can_handle(url):
            raise PlatformDetectError("没有找到该链接对应的平台适配器", platform=platform)

        normalized_request = request.model_copy(update={"url": url})
        result = await adapter.fetch(normalized_request)
        await self._repository.save(result)
        return result
