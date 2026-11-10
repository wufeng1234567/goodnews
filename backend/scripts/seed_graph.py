"""Seed the manually curated Neo4j demo graph.

Run from backend/:
    .venv\\Scripts\\python -m scripts.seed_graph

Or inspect via:
    docker exec goodnews-neo4j cypher-shell -u neo4j -p <password> \
      "MATCH (n:Entity) RETURN count(n);"
"""

from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.knowledge_graph.repository import Neo4jRepository


async def main() -> int:
    settings = get_settings()
    repository = Neo4jRepository(settings)
    await repository.connect()
    try:
        if not repository.available:
            print(f"Neo4j unavailable: {repository.last_error}")
            return 1
        entities, relations = await repository.seed()
        print(f"Graph seeded: entities={entities}, relations={relations}")
        return 0
    finally:
        await repository.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
