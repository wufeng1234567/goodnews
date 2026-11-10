"""Liveness/readiness endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ContainerDep
from app.models.health import DependencyStatus, HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(container: ContainerDep) -> HealthResponse:
    database_ok = await container.database.healthcheck()
    graph_stats = await container.graph_verifier.stats()
    dependencies = [
        DependencyStatus(
            name="postgresql",
            ok=database_ok,
            detail="" if database_ok else container.database.last_error or "unavailable",
        ),
        DependencyStatus(
            name="redis",
            ok=container.cache.available,
            detail="" if container.cache.available else "cache disabled or unavailable",
        ),
        DependencyStatus(
            name="neo4j",
            ok=container.graph_repository.available,
            detail="" if container.graph_repository.available else container.graph_repository.last_error,
        ),
    ]
    all_ok = all(item.ok for item in dependencies)
    return HealthResponse(
        status="ok" if all_ok else "degraded",
        app_name=container.settings.app_name,
        version="0.1.0",
        environment=container.settings.app_env,
        llm_configured=bool(container.settings.llm_api_key),
        dependencies=dependencies,
        graph=graph_stats,
    )
