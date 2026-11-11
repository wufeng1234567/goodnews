"""Persistence for social-platform fetch snapshots."""

from __future__ import annotations

import logging
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.tables import SocialFetchRecord
from app.models.social import SocialFetchResponse

logger = logging.getLogger(__name__)


class SocialFetchRepository:
    def __init__(self, session_factory: async_sessionmaker | None, available: bool) -> None:
        self._session_factory = session_factory
        self._available = available

    @property
    def available(self) -> bool:
        return self._available and self._session_factory is not None

    async def save(self, result: SocialFetchResponse) -> None:
        if not self.available or self._session_factory is None:
            return
        record = SocialFetchRecord(
            id=str(uuid4()),
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
        except Exception as exc:  # noqa: BLE001 - collection result must survive DB hiccups
            logger.warning("Failed to persist social snapshot: %s", exc)
