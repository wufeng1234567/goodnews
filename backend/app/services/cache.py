"""Optional Redis cache.

Redis is deliberately limited to search result caching in the MVP. A cache
failure is always non-fatal; the app continues with live requests.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from redis.asyncio import Redis

from app.core.config import Settings

logger = logging.getLogger(__name__)


class RedisCache:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Redis | None = None
        self.available = False

    async def connect(self) -> None:
        if not self._settings.redis_enabled:
            return
        try:
            self._client = Redis.from_url(
                self._settings.redis_url, encoding="utf-8", decode_responses=True
            )
            await self._client.ping()
            self.available = True
        except Exception as exc:  # noqa: BLE001 - cache is optional
            self.available = False
            logger.warning("Redis unavailable; search caching disabled: %s", exc)

    async def get_json(self, key: str) -> dict[str, Any] | None:
        if not self.available or self._client is None:
            return None
        try:
            raw = await self._client.get(key)
            if raw is None:
                return None
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except Exception as exc:  # noqa: BLE001
            logger.debug("Cache read failed: %s", exc)
            return None

    async def set_json(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        if not self.available or self._client is None:
            return
        try:
            await self._client.set(
                key,
                json.dumps(value, ensure_ascii=False),
                ex=ttl or self._settings.cache_ttl_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Cache write failed: %s", exc)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
