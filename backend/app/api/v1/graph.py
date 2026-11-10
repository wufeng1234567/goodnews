"""Knowledge-graph status route (read-only)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ContainerDep
from app.models.factcheck import GraphStatsResponse

router = APIRouter(prefix="/graph", tags=["knowledge-graph"])


@router.get("/stats", response_model=GraphStatsResponse)
async def graph_stats(container: ContainerDep) -> GraphStatsResponse:
    return await container.graph_verifier.stats()
