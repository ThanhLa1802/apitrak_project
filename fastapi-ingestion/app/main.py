from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.config import settings
from app.routers.ingest import router as ingest_router


def _device_key_func(request) -> str:
    """Rate-limit by API key header, fall back to IP."""
    return request.headers.get("x-api-key") or get_remote_address(request)


limiter = Limiter(key_func=_device_key_func, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create the Redis connection pool once.
    pool = aioredis.ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
        decode_responses=True,
    )
    app.state.redis_pool = pool
    yield
    # Shutdown: drain the pool cleanly.
    await pool.aclose()


app = FastAPI(
    title="Apitrak — Ingestion Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(ingest_router, tags=["Telemetry"])
