"""Search and hot-news API models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    limit: int = Field(default=8, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query cannot be empty")
        return value


class SearchResultItem(BaseModel):
    id: str
    title: str
    url: str
    snippet: str = ""
    source_name: str = ""
    published_at: str | None = None
    provider: str
    rank: int = 0


class SearchResponse(BaseModel):
    query: str
    items: list[SearchResultItem] = Field(default_factory=list)
    provider: str
    cached: bool = False
    fetched_at: datetime
    error: str | None = None


class HotNewsResponse(BaseModel):
    region: str = "CN"
    items: list[SearchResultItem] = Field(default_factory=list)
    provider: str
    cached: bool = False
    fetched_at: datetime
    error: str | None = None
