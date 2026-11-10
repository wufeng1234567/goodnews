"""Fact-check API routes. No authentication in the MVP by explicit scope."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import ContainerDep
from app.models.factcheck import (
    FactCheckHistoryResponse,
    FactCheckRequest,
    FactCheckResponse,
)
from app.services.factcheck_service import FactCheckRunError

router = APIRouter(prefix="/factcheck", tags=["factcheck"])


@router.post("", response_model=FactCheckResponse)
async def create_factcheck(
    payload: FactCheckRequest,
    container: ContainerDep,
) -> FactCheckResponse:
    try:
        return await container.factcheck_service.run(payload)
    except FactCheckRunError as exc:
        # 502: upstream (LLM/crawler/search) failure rather than malformed input.
        raise HTTPException(
            status_code=502,
            detail={"code": "factcheck_failed", "message": str(exc)},
        ) from exc


@router.get("/history", response_model=FactCheckHistoryResponse)
async def factcheck_history(
    container: ContainerDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> FactCheckHistoryResponse:
    items, total = await container.factcheck_repository.list_recent(limit=limit, offset=offset)
    return FactCheckHistoryResponse(items=items, total=total)


@router.get("/{record_id}", response_model=FactCheckResponse)
async def factcheck_detail(
    record_id: str,
    container: ContainerDep,
) -> FactCheckResponse:
    result = await container.factcheck_repository.get(record_id)
    if result is None:
        raise HTTPException(status_code=404, detail="核查记录不存在或数据库未启用")
    return result
