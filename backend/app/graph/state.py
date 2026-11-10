"""Typed LangGraph state.

LangGraph accepts a Pydantic model as the state schema. Nodes return partial
dictionaries, which LangGraph validates against this model after each step.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.models.article import ArticleContent
from app.models.factcheck import (
    Claim,
    Evidence,
    FactCheckRequest,
    GraphVerificationResult,
    TraceStep,
    VerdictResult,
)


class FactCheckState(BaseModel):
    """Single source of truth flowing through the five-node graph."""

    request: FactCheckRequest
    article: ArticleContent | None = None
    claims: list[Claim] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    evidence_round: int = 0
    max_evidence_rounds: int = 2
    evidence_sufficient: bool = False
    next_queries: list[str] = Field(default_factory=list)
    graph_verification: GraphVerificationResult | None = None
    verdict: VerdictResult | None = None
    trace: list[TraceStep] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
