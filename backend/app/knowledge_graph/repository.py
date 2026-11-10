"""Async Neo4j repository owning all Cypher in the application.

No route or service outside this package writes Cypher. This keeps graph access
reviewable and lets the MVP swap Neo4j later without changing business logic.
"""

from __future__ import annotations

import logging
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.core.config import Settings
from app.knowledge_graph.seed_data import ENTITIES, RELATIONS

logger = logging.getLogger(__name__)

_SCHEMA_STATEMENTS = [
    (
        "CREATE CONSTRAINT entity_name_unique IF NOT EXISTS "
        "FOR (e:Entity) REQUIRE e.name IS UNIQUE"
    ),
    "CREATE INDEX entity_type_idx IF NOT EXISTS FOR (e:Entity) ON (e.entity_type)",
]


class Neo4jRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._driver: AsyncDriver | None = None
        self.available = False
        self.last_error = ""

    async def connect(self) -> None:
        if not self._settings.neo4j_enabled:
            self.last_error = "NEO4J_ENABLED=false"
            return
        try:
            self._driver = AsyncGraphDatabase.driver(
                self._settings.neo4j_uri,
                auth=(
                    self._settings.neo4j_user,
                    self._settings.neo4j_password.get_secret_value(),
                ),
                max_connection_lifetime=300,
                connection_timeout=8,
            )
            await self._driver.verify_connectivity()
            async with self._driver.session(database=self._settings.neo4j_database) as session:
                for statement in _SCHEMA_STATEMENTS:
                    await session.run(statement)
            self.available = True
            logger.info("Neo4j connected at %s", self._settings.neo4j_uri)
        except Exception as exc:  # noqa: BLE001 - degrade to insufficient verification
            self.available = False
            self.last_error = str(exc)
            logger.warning("Neo4j unavailable; graph verification will be insufficient: %s", exc)

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()

    async def stats(self) -> tuple[int, int]:
        if not self.available or self._driver is None:
            return 0, 0
        query = (
            "MATCH (e:Entity) WITH count(e) AS entity_count "
            "MATCH ()-[r:RELATED_TO]->() RETURN entity_count, count(r) AS relation_count"
        )
        async with self._driver.session(database=self._settings.neo4j_database) as session:
            record = await (await session.run(query)).single()
        if not record:
            return 0, 0
        return int(record["entity_count"]), int(record["relation_count"])

    async def entity_names(self, limit: int = 120) -> list[str]:
        if not self.available or self._driver is None:
            return []
        query = "MATCH (e:Entity) RETURN e.name AS name ORDER BY name LIMIT $limit"
        async with self._driver.session(database=self._settings.neo4j_database) as session:
            result = await session.run(query, limit=limit)
            records = await result.data()
        return [str(record["name"]) for record in records if record.get("name")]

    async def lookup_relations(self, subject: str, predicate: str) -> list[dict[str, Any]]:
        """Return confirmed relations for subject+predicate, exact alias match only."""
        if not self.available or self._driver is None:
            return []
        query = """
        MATCH (s:Entity)-[r:RELATED_TO]->(o:Entity)
        WHERE (
            toLower(s.name) = toLower($subject)
            OR any(alias IN coalesce(s.aliases, []) WHERE toLower(alias) = toLower($subject))
        )
        AND toLower(r.predicate) = toLower($predicate)
        RETURN s.name AS subject, r.predicate AS predicate, o.name AS object,
               coalesce(r.confidence, 1.0) AS confidence, coalesce(r.note, '') AS note
        ORDER BY object
        LIMIT 20
        """
        async with self._driver.session(database=self._settings.neo4j_database) as session:
            result = await session.run(query, subject=subject, predicate=predicate)
            return await result.data()

    async def seed(self) -> tuple[int, int]:
        """Idempotently upsert the manually curated demo graph."""
        if not self.available or self._driver is None:
            raise RuntimeError(f"Neo4j 不可用: {self.last_error or 'not connected'}")
        entities = [entity.model_dump() for entity in ENTITIES]
        relations = [relation.model_dump() for relation in RELATIONS]
        async with self._driver.session(database=self._settings.neo4j_database) as session:
            await session.run(
                """
                UNWIND $entities AS entity
                MERGE (e:Entity {name: entity.name})
                SET e.entity_type = entity.entity_type,
                    e.aliases = entity.aliases,
                    e.description = entity.description
                """,
                entities=entities,
            )
            await session.run(
                """
                UNWIND $relations AS relation
                MATCH (s:Entity {name: relation.subject})
                MATCH (o:Entity {name: relation.object})
                MERGE (s)-[r:RELATED_TO {predicate: relation.predicate}]->(o)
                SET r.confidence = relation.confidence,
                    r.note = relation.note,
                    r.source = relation.source
                """,
                relations=relations,
            )
        return await self.stats()
