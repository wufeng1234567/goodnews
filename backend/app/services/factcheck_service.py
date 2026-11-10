"""Use-case orchestration for one synchronous fact-check request."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings
from app.crawler.service import ArticleFetchError
from app.db.repository import FactCheckRepository
from app.graph.state import FactCheckState
from app.llm.client import LLMError
from app.models.common import InputType
from app.models.factcheck import FactCheckRequest, FactCheckResponse

logger = logging.getLogger(__name__)


class FactCheckRunError(RuntimeError):
    """A user-facing failure while running the fact-check graph."""


class FactCheckService:
    def __init__(
        self,
        settings: Settings,
        graph: Any,
        repository: FactCheckRepository,
    ) -> None:
        self._settings = settings
        self._graph = graph
        self._repository = repository

    async def run(self, request: FactCheckRequest) -> FactCheckResponse:
        if len(request.content) > self._settings.max_factcheck_input_chars:
            raise FactCheckRunError("输入内容过长，请控制在 5 万字以内")

        max_rounds = (
            request.max_evidence_rounds
            if request.max_evidence_rounds is not None
            else self._settings.factcheck_max_evidence_rounds
        )
        initial = FactCheckState(
            request=request,
            max_evidence_rounds=max_rounds,
        )
        started = time.perf_counter()
        try:
            raw_result = await self._graph.ainvoke(
                initial,
                config={"recursion_limit": 30},
            )
        except (LLMError, ArticleFetchError) as exc:
            raise FactCheckRunError(str(exc)) from exc
        except Exception as exc:
            logger.exception("Fact-check graph failed")
            raise FactCheckRunError(f"核查流程执行失败: {exc}") from exc

        if isinstance(raw_result, FactCheckState):
            state = raw_result
        else:
            state = FactCheckState.model_validate(raw_result)
        if state.verdict is None or state.article is None:
            raise FactCheckRunError("核查流程未产生完整结果")

        resolved_input_type = (
            InputType.URL
            if state.article.fetched_with in {"scrapy", "scrapy_playwright"}
            else InputType.TEXT
        )
        response = FactCheckResponse(
            **state.verdict.model_dump(),
            input_type=resolved_input_type,
            source_url=state.article.url,
            article=state.article,
            trace=state.trace,
            warnings=state.warnings,
            duration_ms=int((time.perf_counter() - started) * 1000),
            created_at=datetime.now(UTC),
        )
        await self._repository.save(response, request.content)
        return response
