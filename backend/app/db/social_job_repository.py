"""Persistence for background social comment-collection jobs."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.tables import SocialFetchJob
from app.models.social import (
    SocialJobState,
    SocialJobStatus,
    SocialPlatform,
)

logger = logging.getLogger(__name__)


class SocialJobRepository:
    def __init__(self, session_factory: async_sessionmaker | None, available: bool) -> None:
        self._session_factory = session_factory
        self._available = available

    @property
    def available(self) -> bool:
        return self._available and self._session_factory is not None

    async def create(
        self,
        *,
        platform: SocialPlatform,
        url: str,
        max_comments: int,
    ) -> SocialJobStatus:
        if not self.available or self._session_factory is None:
            raise RuntimeError("数据库不可用，无法创建后台评论任务")
        job_id = str(uuid4())
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            session.add(
                SocialFetchJob(
                    id=job_id,
                    platform=platform.value,
                    url=url,
                    state=SocialJobState.QUEUED.value,
                    max_comments=max_comments,
                    total_fetched=0,
                    progress=0,
                    error="",
                )
            )
            await session.commit()
        return SocialJobStatus(
            id=job_id,
            platform=platform,
            url=url,
            state=SocialJobState.QUEUED,
            max_comments=max_comments,
            created_at=now,
            updated_at=now,
        )

    async def update(
        self,
        job_id: str,
        *,
        state: SocialJobState | None = None,
        progress: int | None = None,
        total_fetched: int | None = None,
        record_id: str | None = None,
        error: str | None = None,
        finished: bool = False,
    ) -> None:
        if not self.available or self._session_factory is None:
            return
        values: dict[str, object] = {"updated_at": datetime.now(UTC)}
        if state is not None:
            values["state"] = state.value
        if progress is not None:
            values["progress"] = progress
        if total_fetched is not None:
            values["total_fetched"] = total_fetched
        if record_id is not None:
            values["record_id"] = record_id
        if error is not None:
            values["error"] = error
        if finished:
            values["finished_at"] = datetime.now(UTC)
        async with self._session_factory() as session:
            await session.execute(
                update(SocialFetchJob).where(SocialFetchJob.id == job_id).values(**values)
            )
            await session.commit()

    async def get(self, job_id: str) -> SocialJobStatus | None:
        if not self.available or self._session_factory is None:
            return None
        async with self._session_factory() as session:
            row = await session.get(SocialFetchJob, job_id)
            if row is None:
                return None
            return SocialJobStatus(
                id=row.id,
                platform=SocialPlatform(row.platform),
                url=row.url,
                state=SocialJobState(row.state),
                progress=row.progress,
                max_comments=row.max_comments,
                total_fetched=row.total_fetched,
                record_id=row.record_id,
                error=row.error or "",
                created_at=row.created_at,
                updated_at=row.updated_at,
                finished_at=row.finished_at,
            )

    async def mark_interrupted(self) -> None:
        """Mark jobs left running after a process restart as failed."""
        if not self.available or self._session_factory is None:
            return
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(SocialFetchJob).where(
                        SocialFetchJob.state.in_(
                            [SocialJobState.QUEUED.value, SocialJobState.RUNNING.value]
                        )
                    )
                )
            ).all()
            for row in rows:
                row.state = SocialJobState.FAILED.value
                row.error = "服务重启导致任务中断，请重新发起。"
                row.finished_at = datetime.now(UTC)
            if rows:
                await session.commit()
