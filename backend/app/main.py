"""goodnews FastAPI entrypoint.

Run from backend/:
    .venv\\Scripts\\uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.bootstrap import AppContainer, build_container
from app.core.config import Settings, get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info("Starting %s (%s)", resolved_settings.app_name, resolved_settings.app_env)
        container: AppContainer = await build_container(resolved_settings)
        app.state.container = container
        logger.info(
            "Ready at %s%s/health | graph=%s",
            "http://127.0.0.1:8000",
            resolved_settings.api_prefix,
            "connected" if container.graph_repository.available else "unavailable",
        )
        try:
            yield
        finally:
            await container.close()
            logger.info("goodnews stopped")

    app = FastAPI(
        title="goodnews API",
        version="0.1.0",
        description=(
            "新闻热点搜索、信息探索与假新闻分析 MVP。"
            "LangGraph orchestrates fetch -> claims -> evidence -> graph verify -> adjudicate."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=resolved_settings.api_prefix)

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        return {
            "name": "goodnews",
            "version": "0.1.0",
            "docs": "/docs",
            "health": f"{resolved_settings.api_prefix}/health",
        }

    return app


app = create_app()
