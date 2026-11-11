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
from app.db.social_job_repository import SocialJobRepository
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
from app.services.social_auth import SocialAuthManager
from app.services.social_jobs import SocialJobService
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
    social_auth_manager: SocialAuthManager
    social_job_repository: SocialJobRepository
    social_job_service: SocialJobService
    compiled_graph: Any = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    async def close(self) -> None:
        await self.social_job_service.close()
        await self.social_auth_manager.close()
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
    social_auth_manager = SocialAuthManager(settings)
    social_auth_manager.start_background()
    social_service = SocialService(settings, social_repository, social_auth_manager)
    social_job_repository = SocialJobRepository(
        database.session_factory, database.available
    )
    await social_job_repository.mark_interrupted()
    social_job_service = SocialJobService(
        social_service=social_service,
        job_repo=social_job_repository,
        record_repo=social_repository,
        max_full_comments=settings.social_full_max_comments,
    )

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
        social_auth_manager=social_auth_manager,
        social_job_repository=social_job_repository,
        social_job_service=social_job_service,
        compiled_graph=compiled_graph,
    )
