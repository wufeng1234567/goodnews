"""Async SQLAlchemy engine and schema bootstrap."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.db.tables import Base

logger = logging.getLogger(__name__)

VECTOR_PLACEHOLDER_DDL = """
CREATE TABLE IF NOT EXISTS article_embeddings (
    id BIGSERIAL PRIMARY KEY,
    article_key TEXT NOT NULL,
    embedding vector(1024),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


class Database:
    """Owns the engine and session factory for the app lifespan."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker | None = None
        self.available = False
        self.last_error = ""

    async def connect(self) -> None:
        if not self._settings.database_enabled:
            self.last_error = "DATABASE_ENABLED=false"
            return
        self.engine = create_async_engine(
            self._settings.sqlalchemy_database_url,
            echo=self._settings.database_echo,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
        )
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        try:
            async with self.engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
                await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                await connection.execute(text(VECTOR_PLACEHOLDER_DDL))
            self.available = True
            logger.info("PostgreSQL connected; pgvector placeholder table is ready")
        except Exception as exc:  # noqa: BLE001 - startup should degrade, not crash
            self.available = False
            self.last_error = str(exc)
            logger.warning("PostgreSQL unavailable; history will be disabled: %s", exc)

    async def healthcheck(self) -> bool:
        if not self.engine or not self.available:
            return False
        try:
            async with self.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            return True
        except Exception:  # noqa: BLE001
            return False

    async def close(self) -> None:
        if self.engine is not None:
            await self.engine.dispose()
