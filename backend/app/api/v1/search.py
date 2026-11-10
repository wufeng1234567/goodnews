"""Hot-news and keyword search routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ContainerDep
from app.models.search import HotNewsResponse, SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search_news(
    payload: SearchRequest,
    container: ContainerDep,
) -> SearchResponse:
    return await container.search_service.search(payload.query, payload.limit)


@router.get("/hot", response_model=HotNewsResponse)
async def hot_news(
    container: ContainerDep,
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
    region: Annotated[str, Query(max_length=8)] = "CN",
) -> HotNewsResponse:
    return await container.search_service.hot(limit=limit, region=region)
