"""Unified social-content and comment contracts.

Every platform adapter returns these exact models. The frontend mirrors them in
``frontend/src/types/social.ts``; keep both sides in sync.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, computed_field, field_validator


class SocialPlatform(str, Enum):
    XIAOHONGSHU = "xiaohongshu"
    DOUYIN = "douyin"
    BILIBILI = "bilibili"


class SocialContentType(str, Enum):
    VIDEO = "video"
    NOTE = "note"
    ARTICLE = "article"
    UNKNOWN = "unknown"


class SocialAuthor(BaseModel):
    id: str = ""
    name: str = "未知作者"
    handle: str = ""
    avatar_url: str | None = None
    profile_url: str | None = None
    follower_count: int | None = None


class SocialMetrics(BaseModel):
    """Raw platform counters. ``None`` means the platform did not expose it."""

    view_count: int | None = None
    play_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None
    share_count: int | None = None
    collect_count: int | None = None
    coin_count: int | None = None
    danmaku_count: int | None = None
    extra: dict[str, int] = Field(default_factory=dict)

    @computed_field
    @property
    def total_engagement(self) -> int:
        values = [
            self.like_count,
            self.comment_count,
            self.share_count,
            self.collect_count,
            self.coin_count,
        ]
        return sum(value for value in values if value is not None)


class SocialContent(BaseModel):
    platform: SocialPlatform
    content_id: str
    content_type: SocialContentType = SocialContentType.UNKNOWN
    url: str
    title: str
    description: str = ""
    author: SocialAuthor = Field(default_factory=SocialAuthor)
    published_at: datetime | None = None
    cover_url: str | None = None
    media_urls: list[str] = Field(default_factory=list)
    duration_seconds: int | None = None
    tags: list[str] = Field(default_factory=list)
    metrics: SocialMetrics = Field(default_factory=SocialMetrics)


class SocialComment(BaseModel):
    id: str
    content_id: str
    parent_id: str | None = None
    text: str
    author_name: str = "匿名用户"
    author_id: str = ""
    author_avatar_url: str | None = None
    like_count: int = 0
    reply_count: int = 0
    created_at: datetime | None = None
    replies: list[SocialComment] = Field(default_factory=list)


SocialComment.model_rebuild()


class SocialFetchRequest(BaseModel):
    url: str = Field(min_length=5, max_length=2_000)
    # 0 means "full collection" for the background job; quick previews use
    # small positive values. The job service enforces a hard safety ceiling.
    max_comments: int = Field(default=30, ge=0, le=50_000)
    include_replies: bool = True

    @field_validator("url")
    @classmethod
    def extract_url(cls, value: str) -> str:
        """Accept pasted share text containing one URL, not only a bare URL."""
        match = re.search(r"https?://[^\s\u3000]+", value.strip())
        if not match:
            raise ValueError("请粘贴小红书/抖音/Bilibili 的内容链接")
        return match.group(0).rstrip("，。,.；;）)】]")


class SocialFetchResponse(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    platform: SocialPlatform
    content: SocialContent
    comments: list[SocialComment] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_comments_fetched: int = 0
    has_more: bool = False
    collection_method: Literal["public_api", "browser_api", "browser_dom"] = "public_api"
    auth_mode: Literal["none", "cookie", "storage_state"] = "none"
    warnings: list[str] = Field(default_factory=list)


class SocialPlatformInfo(BaseModel):
    platform: SocialPlatform
    label: str
    supported: bool
    needs_login_for_comments: bool
    login_command: str
    note: str


class SocialPlatformListResponse(BaseModel):
    platforms: list[SocialPlatformInfo]


class SocialAuthState(str, Enum):
    NOT_LOGGED_IN = "not_logged_in"
    WAITING = "waiting"
    LOGGED_IN = "logged_in"
    EXPIRED = "expired"
    FAILED = "failed"


class SocialAuthStatus(BaseModel):
    platform: SocialPlatform
    state: SocialAuthState
    logged_in: bool = False
    account_name: str | None = None
    message: str = ""
    expires_at: datetime | None = None
    last_login_at: datetime | None = None
    last_checked_at: datetime | None = None
    last_refreshed_at: datetime | None = None
    auto_refresh: bool = True


class SocialAuthStatusListResponse(BaseModel):
    statuses: list[SocialAuthStatus]


class SocialAuthActionRequest(BaseModel):
    platform: SocialPlatform


class SocialJobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SocialJobCreateRequest(BaseModel):
    url: str = Field(min_length=5, max_length=2_000)
    include_replies: bool = True
    # 0 means all available comments, bounded by the server ceiling.
    max_comments: int = Field(default=0, ge=0, le=50_000)

    @field_validator("url")
    @classmethod
    def extract_job_url(cls, value: str) -> str:
        match = re.search(r"https?://[^\s\u3000]+", value.strip())
        if not match:
            raise ValueError("请粘贴小红书/抖音/Bilibili 的内容链接")
        return match.group(0).rstrip("，。,.；;）)】]")


class SocialJobStatus(BaseModel):
    id: str
    platform: SocialPlatform
    url: str
    state: SocialJobState
    progress: int = Field(default=0, ge=0, le=100)
    max_comments: int = 0
    total_fetched: int = 0
    record_id: str | None = None
    error: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    finished_at: datetime | None = None
