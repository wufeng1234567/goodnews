"""SQLAlchemy 2.0 table definitions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class FactCheckRecord(Base):
    """Immutable snapshot of one fact-check run.

    Keeping the complete response as JSONB is a deliberate MVP trade-off: it
    makes history rendering exact and avoids premature normalization. Later
    refactor point: split claims/evidence into relational tables for analytics.
    """

    __tablename__ = "factcheck_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    input_type: Mapped[str] = mapped_column(String(16), index=True)
    input_preview: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    article_title: Mapped[str] = mapped_column(Text)
    verdict: Mapped[str] = mapped_column(String(32), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    result: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class SocialFetchRecord(Base):
    """One social-platform content + comment snapshot.

    The first iteration stores the normalized DTO as JSONB. Raw API payloads
    are intentionally not persisted because they contain volatile signed URLs
    and large unrelated fields. Later refactor point: split content, comments
    and author snapshots into normalized tables for analytics.
    """

    __tablename__ = "social_fetch_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    platform: Mapped[str] = mapped_column(String(24), index=True)
    content_id: Mapped[str] = mapped_column(String(128), index=True)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    author_name: Mapped[str] = mapped_column(Text)
    comments_fetched: Mapped[int] = mapped_column(Integer, default=0)
    metrics: Mapped[dict] = mapped_column(JSONB)
    result: Mapped[dict] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class SocialFetchJob(Base):
    """Background full-comment collection job."""

    __tablename__ = "social_fetch_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    platform: Mapped[str] = mapped_column(String(24), index=True)
    url: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(16), index=True)
    max_comments: Mapped[int] = mapped_column(Integer, default=0)
    total_fetched: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    record_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
