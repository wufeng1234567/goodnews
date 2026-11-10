"""Ports used by graph nodes.

Depending on protocols keeps the LangGraph layer independent from concrete
crawler/search/Neo4j implementations and lets tests inject deterministic fakes.
"""

from __future__ import annotations

from typing import Protocol

from app.models.article import ArticleContent
from app.models.factcheck import (
    Claim,
    Evidence,
    FactCheckRequest,
    GraphVerificationResult,
)


class ArticleProvider(Protocol):
    async def resolve(self, request: FactCheckRequest) -> ArticleContent: ...


class EvidenceProvider(Protocol):
    async def retrieve(
        self,
        claims: list[Claim],
        queries: list[str],
        existing: list[Evidence],
    ) -> list[Evidence]: ...


class GraphVerifier(Protocol):
    async def verify(
        self,
        claims: list[Claim],
        round_number: int,
    ) -> GraphVerificationResult: ...
