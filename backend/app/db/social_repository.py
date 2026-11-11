"""Persistence for social-platform fetch snapshots."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.tables import SocialFetchRecord
from app.models.social import SocialFetchResponse, SocialHistoryItem, SocialPlatform

logger = logging.getLogger(__name__)


class SocialFetchRepository:
    def __init__(self, session_factory: async_sessionmaker | None, available: bool) -> None:
        self._session_factory = session_factory
        self._available = available

    @property
    def available(self) -> bool:
        return self._available and self._session_factory is not None

    async def save(self, result: SocialFetchResponse) -> bool:
        if not self.available or self._session_factory is None:
            return False
        record = SocialFetchRecord(
            id=result.id,
            platform=result.platform.value,
            content_id=result.content.content_id[:128],
            url=result.content.url,
            title=result.content.title,
            author_name=result.content.author.name,
            comments_fetched=result.total_comments_fetched,
            metrics=result.content.metrics.model_dump(mode="json"),
            result=result.model_dump(mode="json"),
        )
        try:
            async with self._session_factory() as session:
                session.add(record)
                await session.commit()
            return True
        except Exception as exc:  # noqa: BLE001 - collection result must survive DB hiccups
            logger.warning("Failed to persist social snapshot: %s", exc)
            return False

    async def get(self, record_id: str) -> SocialFetchResponse | None:
        if not self.available or self._session_factory is None:
            return None
        async with self._session_factory() as session:
            record = await session.get(SocialFetchRecord, record_id)
            if record is None:
                return None
            return SocialFetchResponse.model_validate(record.result)

    async def list_recent(
        self,
        limit: int = 30,
        platform: SocialPlatform | None = None,
    ) -> list[SocialHistoryItem]:
        if not self.available or self._session_factory is None:
            return []
        async with self._session_factory() as session:
            query = select(SocialFetchRecord).order_by(SocialFetchRecord.fetched_at.desc())
            if platform is not None:
                query = query.where(SocialFetchRecord.platform == platform.value)
            records = (await session.scalars(query.limit(limit))).all()
            return [
                SocialHistoryItem(
                    id=record.id,
                    platform=SocialPlatform(record.platform),
                    content_id=record.content_id,
                    url=record.url,
                    title=record.title,
                    author_name=record.author_name,
                    comments_fetched=record.comments_fetched,
                    fetched_at=record.fetched_at,
                )
                for record in records
            ]
