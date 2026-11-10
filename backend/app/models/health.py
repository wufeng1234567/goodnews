"""Health-check response models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.models.factcheck import GraphStatsResponse


class DependencyStatus(BaseModel):
    name: str
    ok: bool
    detail: str = ""


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    app_name: str
    version: str
    environment: str
    llm_configured: bool
    dependencies: list[DependencyStatus] = Field(default_factory=list)
    graph: GraphStatsResponse
