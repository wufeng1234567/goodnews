"""SQLAlchemy 2.0 table definitions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text, func
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
