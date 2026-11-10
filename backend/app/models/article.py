"""Article and input models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ArticleContent(BaseModel):
    """Normalized article body passed between fetch and claim extraction."""

    title: str = Field(default="未命名文章", max_length=500)
    url: str | None = None
    text: str = Field(min_length=1)
    author: str | None = None
    published_at: str | None = None
    source_name: str | None = None
    fetched_with: Literal["input_text", "scrapy", "scrapy_playwright"] = "input_text"
    word_count: int = Field(default=0, ge=0)

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("article text cannot be empty")
        return value
