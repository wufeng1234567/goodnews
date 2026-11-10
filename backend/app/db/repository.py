"""Persistence operations for fact-check history."""

from __future__ import annotations

import logging
from datetime import UTC

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.tables import FactCheckRecord
from app.models.factcheck import (
    FactCheckHistoryItem,
    FactCheckResponse,
)

logger = logging.getLogger(__name__)


class FactCheckRepository:
    def __init__(self, session_factory: async_sessionmaker | None, available: bool) -> None:
        self._session_factory = session_factory
        self._available = available

    @property
    def available(self) -> bool:
        return self._available and self._session_factory is not None

    async def save(self, result: FactCheckResponse, input_content: str) -> None:
        if not self.available or self._session_factory is None:
            return
        record = FactCheckRecord(
            id=result.id,
            input_type=result.input_type.value,
            input_preview=input_content[:500],
            source_url=result.source_url,
            article_title=result.article.title,
            verdict=result.verdict.value,
            confidence=result.confidence,
            result=result.model_dump(mode="json"),
        )
        try:
            async with self._session_factory() as session:
                session.add(record)
                await session.commit()
        except Exception as exc:  # noqa: BLE001 - history failure must not destroy analysis
            logger.warning("Failed to persist fact-check %s: %s", result.id, exc)

    async def get(self, record_id: str) -> FactCheckResponse | None:
        if not self.available or self._session_factory is None:
            return None
        async with self._session_factory() as session:
            record = await session.get(FactCheckRecord, record_id)
            if record is None:
                return None
            return FactCheckResponse.model_validate(record.result)

    async def list_recent(self, limit: int = 10, offset: int = 0) -> tuple[list[FactCheckHistoryItem], int]:
        if not self.available or self._session_factory is None:
            return [], 0
        async with self._session_factory() as session:
            total = await session.scalar(select(func.count()).select_from(FactCheckRecord)) or 0
            rows = (
                await session.scalars(
                    select(FactCheckRecord)
                    .order_by(FactCheckRecord.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            ).all()
        items = [
            FactCheckHistoryItem(
                id=row.id,
                input_preview=row.input_preview,
                input_type=row.input_type,
                source_url=row.source_url,
                verdict=row.verdict,
                confidence=row.confidence,
                created_at=row.created_at.astimezone(UTC)
                if row.created_at.tzinfo
                else row.created_at,
            )
            for row in rows
        ]
        return items, int(total)
