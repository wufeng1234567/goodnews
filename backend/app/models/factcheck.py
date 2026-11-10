"""Public fact-check API contract.

Important: the Vue types in ``frontend/src/types/factcheck.ts`` mirror these
models field-for-field. Change both sides together.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.article import ArticleContent
from app.models.common import (
    EvidenceStance,
    GraphMatchStatus,
    GraphVerificationStatus,
    InputType,
    NodeStatus,
    Verdict,
)


class FactCheckRequest(BaseModel):
    input_type: InputType = InputType.AUTO
    content: str = Field(min_length=1, max_length=50_000)
    language: str = Field(default="zh", max_length=16)
    max_evidence_rounds: int | None = Field(default=None, ge=0, le=3)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("content cannot be empty")
        return value

    @model_validator(mode="after")
    def validate_url_input(self) -> FactCheckRequest:
        if self.input_type is InputType.URL:
            parsed = urlsplit(self.content)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError("input_type=url 时必须提供有效的 http/https 链接")
        return self


class Claim(BaseModel):
    id: str
    text: str
    entities: list[str] = Field(default_factory=list)
    importance: Literal["high", "medium", "low"] = "medium"
    verdict: Verdict | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    reasoning: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class Evidence(BaseModel):
    id: str
    claim_ids: list[str] = Field(default_factory=list)
    title: str
    url: str
    snippet: str = ""
    content_excerpt: str = ""
    source_name: str = ""
    published_at: str | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    stance: EvidenceStance = EvidenceStance.NEUTRAL
    relevance: float = Field(default=0.5, ge=0, le=1)
    query: str = ""


class GraphMatch(BaseModel):
    claim_id: str
    subject: str
    predicate: str
    claimed_object: str
    graph_object: str | None = None
    status: GraphMatchStatus
    confidence: float = Field(default=0.8, ge=0, le=1)
    note: str = ""


class GraphVerificationResult(BaseModel):
    status: GraphVerificationStatus = GraphVerificationStatus.INSUFFICIENT
    matches: list[GraphMatch] = Field(default_factory=list)
    checked_claims: int = 0
    graph_entities: int = 0
    graph_relations: int = 0
    notes: list[str] = Field(default_factory=list)
    elapsed_ms: int = 0
    round: int = 0


class VerdictResult(BaseModel):
    verdict: Verdict
    confidence: float = Field(ge=0, le=1)
    claims: list[Claim] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    graph_verification: GraphVerificationResult
    reasoning: str


class TraceStep(BaseModel):
    node: str
    label: str
    status: NodeStatus
    detail: str = ""
    duration_ms: int = 0
    sequence: int = 0


class FactCheckResponse(VerdictResult):
    id: str = Field(default_factory=lambda: str(uuid4()))
    input_type: InputType
    source_url: str | None = None
    article: ArticleContent
    trace: list[TraceStep] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    duration_ms: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FactCheckHistoryItem(BaseModel):
    id: str
    input_preview: str
    input_type: InputType
    source_url: str | None = None
    verdict: Verdict
    confidence: float
    created_at: datetime


class FactCheckHistoryResponse(BaseModel):
    items: list[FactCheckHistoryItem] = Field(default_factory=list)
    total: int = 0


class GraphStatsResponse(BaseModel):
    entity_count: int
    relation_count: int
    available: bool
    note: str = ""
