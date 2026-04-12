from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import Request

from app.config import settings

# Connection pool created once at app startup (lifespan).
_pool: aioredis.ConnectionPool | None = None


def create_pool() -> aioredis.ConnectionPool:
    return aioredis.ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
        decode_responses=True,
    )


def get_pool() -> aioredis.ConnectionPool:
    if _pool is None:
        raise RuntimeError("Redis pool has not been initialised. Check lifespan.")
    return _pool


async def get_redis(request: Request) -> AsyncGenerator[aioredis.Redis, None]:
    """FastAPI dependency — yields a Redis client from the shared pool."""
    client = aioredis.Redis(connection_pool=request.app.state.redis_pool)
    try:
        yield client
    finally:
        await client.aclose()
