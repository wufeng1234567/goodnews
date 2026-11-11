"""Background full-comment collection jobs.

Large comment sets can take minutes and produce very large payloads, so they
must not be tied to one long browser/API request. This is an in-process job
runner for the MVP; jobs and progress live in PostgreSQL. Later refactor point:
move the runner to Celery/RQ or a dedicated worker.
"""

from __future__ import annotations

import asyncio
import logging

from app.db.social_job_repository import SocialJobRepository
from app.db.social_repository import SocialFetchRepository
from app.models.social import (
    SocialFetchRequest,
    SocialFetchResponse,
    SocialJobCreateRequest,
    SocialJobState,
    SocialJobStatus,
)
from app.platforms.base import (
    PlatformDetectError,
    SocialPlatformError,
    detect_platform,
    extract_first_url,
)
from app.services.social_service import SocialService

logger = logging.getLogger(__name__)


class SocialJobService:
    def __init__(
        self,
        *,
        social_service: SocialService,
        job_repo: SocialJobRepository,
        record_repo: SocialFetchRepository,
        max_full_comments: int = 100_000,
    ) -> None:
        self._social_service = social_service
        self._job_repo = job_repo
        self._record_repo = record_repo
        self._max_full_comments = max_full_comments
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def create(self, request: SocialJobCreateRequest) -> SocialJobStatus:
        url = extract_first_url(request.url)
        platform = detect_platform(url)
        max_comments = request.max_comments or self._max_full_comments
        job = await self._job_repo.create(
            platform=platform,
            url=url,
            max_comments=max_comments,
        )
        task = asyncio.create_task(self._run(job.id, request.model_copy(update={"url": url})))
        self._tasks[job.id] = task
        task.add_done_callback(lambda _: self._tasks.pop(job.id, None))
        return job

    async def _run(self, job_id: str, request: SocialJobCreateRequest) -> None:
        try:
            await self._job_repo.update(
                job_id,
                state=SocialJobState.RUNNING,
                progress=5,
            )
            result = await self._social_service.fetch(
                SocialFetchRequest(
                    url=request.url,
                    max_comments=request.max_comments or self._max_full_comments,
                    include_replies=request.include_replies,
                )
            )
            await self._job_repo.update(
                job_id,
                state=SocialJobState.COMPLETED,
                progress=100,
                total_fetched=result.total_comments_fetched,
                record_id=result.id,
                error="",
                finished=True,
            )
        except PlatformDetectError as exc:
            await self._fail(job_id, exc.message)
        except SocialPlatformError as exc:
            await self._fail(job_id, exc.message)
        except Exception as exc:
            logger.exception("Social full-comment job %s failed", job_id)
            await self._fail(job_id, f"全量评论任务失败：{exc}")

    async def _fail(self, job_id: str, message: str) -> None:
        await self._job_repo.update(
            job_id,
            state=SocialJobState.FAILED,
            progress=100,
            error=message[:1_000],
            finished=True,
        )

    async def status(self, job_id: str) -> SocialJobStatus | None:
        return await self._job_repo.get(job_id)

    async def result(self, job_id: str) -> SocialFetchResponse | None:
        job = await self._job_repo.get(job_id)
        if job is None or not job.record_id:
            return None
        return await self._record_repo.get(job.record_id)

    async def close(self) -> None:
        for task in list(self._tasks.values()):
            task.cancel()
        for task in list(self._tasks.values()):
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()
