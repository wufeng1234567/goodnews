"""Application composition root.

One container is created during FastAPI lifespan and shared by read-only
requests. It owns long-lived clients and closes them on shutdown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings
from app.crawler.service import ScrapyArticleFetcher
from app.db.repository import FactCheckRepository
from app.db.session import Database
from app.db.social_repository import SocialFetchRepository
from app.graph.builder import build_factcheck_graph
from app.graph.nodes import FactCheckNodes
from app.knowledge_graph.repository import Neo4jRepository
from app.knowledge_graph.verifier import GraphVerifier
from app.llm.client import LLMClient
from app.services.article_service import ArticleService
from app.services.cache import RedisCache
from app.services.evidence_service import EvidenceService
from app.services.factcheck_service import FactCheckService
from app.services.search_service import SearchService
from app.services.social_service import SocialService


@dataclass
class AppContainer:
    settings: Settings
    database: Database
    cache: RedisCache
    graph_repository: Neo4jRepository
    graph_verifier: GraphVerifier
    llm: LLMClient
    article_service: ArticleService
    search_service: SearchService
    evidence_service: EvidenceService
    factcheck_service: FactCheckService
    factcheck_repository: FactCheckRepository
    social_service: SocialService
    social_repository: SocialFetchRepository
    compiled_graph: Any = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    async def close(self) -> None:
        await self.llm.aclose()
        await self.graph_repository.close()
        await self.cache.close()
        await self.database.close()


async def build_container(settings: Settings) -> AppContainer:
    database = Database(settings)
    await database.connect()

    cache = RedisCache(settings)
    await cache.connect()

    graph_repository = Neo4jRepository(settings)
    await graph_repository.connect()

    llm = LLMClient(settings)
    fetcher = ScrapyArticleFetcher(settings)
    article_service = ArticleService(settings, fetcher)
    search_service = SearchService(settings, cache)
    evidence_service = EvidenceService(settings, search_service, fetcher)
    graph_verifier = GraphVerifier(graph_repository, llm)

    nodes = FactCheckNodes(
        settings=settings,
        llm=llm,
        articles=article_service,
        evidence=evidence_service,
        graph=graph_verifier,
    )
    compiled_graph = build_factcheck_graph(nodes)
    factcheck_repository = FactCheckRepository(
        database.session_factory, database.available
    )
    factcheck_service = FactCheckService(settings, compiled_graph, factcheck_repository)
    social_repository = SocialFetchRepository(
        database.session_factory, database.available
    )
    social_service = SocialService(settings, social_repository)

    return AppContainer(
        settings=settings,
        database=database,
        cache=cache,
        graph_repository=graph_repository,
        graph_verifier=graph_verifier,
        llm=llm,
        article_service=article_service,
        search_service=search_service,
        evidence_service=evidence_service,
        factcheck_service=factcheck_service,
        factcheck_repository=factcheck_repository,
        social_service=social_service,
        social_repository=social_repository,
        compiled_graph=compiled_graph,
    )
