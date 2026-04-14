import pytest
import fakeredis.aioredis
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.redis_client import get_redis
from shared.redis_keys import device_creds_key, device_position_key, TELEMETRY_STREAM


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def override_redis(fake_redis):
    async def _get_redis_override():
        yield fake_redis
    app.dependency_overrides[get_redis] = _get_redis_override
    yield fake_redis
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_auth_valid_key(override_redis):
    key_hash = "abc123"
    await override_redis.hset(
        device_creds_key(key_hash),
        mapping={"device_id": "d1d1d1d1-d1d1-d1d1-d1d1-d1d1d1d1d1d1",
                 "org_id": "a0a0a0a0-a0a0-a0a0-a0a0-a0a0a0a0a0a0",
                 "asset_id": "b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2",
                 "is_active": "true"},
    )
    import hashlib
    raw_key = hashlib.sha256(b"abc123").hexdigest()  # this is not the raw key; see test_ingest below


@pytest.mark.asyncio
async def test_ingest_happy_path(override_redis):
    import hashlib
    raw_key = "my-secret-device-key"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    device_id = "d1d1d1d1-d1d1-d1d1-d1d1-d1d1d1d1d1d1"
    org_id = "a0a0a0a0-a0a0-a0a0-a0a0-a0a0a0a0a0a0"
    asset_id = "b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2"

    await override_redis.hset(
        device_creds_key(key_hash),
        mapping={"device_id": device_id, "org_id": org_id,
                 "asset_id": asset_id, "is_active": "true"},
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/ingest",
            json={"lat": 10.762622, "lng": 106.660172,
                  "timestamp": "2026-04-11T10:00:00Z",
                  "speed": 30.5, "heading": 90.0, "accuracy": 5.0, "battery": 85},
            headers={"x-api-key": raw_key},
        )

    assert response.status_code == 202

    pos = await override_redis.hgetall(device_position_key(device_id))
    assert pos["lat"] == "10.762622"
    assert pos["lng"] == "106.660172"

    stream_len = await override_redis.xlen(TELEMETRY_STREAM)
    assert stream_len == 1


@pytest.mark.asyncio
async def test_ingest_out_of_order_ping_does_not_overwrite_newer(override_redis):
    """A late-arriving (older timestamp) ping must not overwrite a newer position."""
    import hashlib
    raw_key = "my-secret-device-key"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    device_id = "d1d1d1d1-d1d1-d1d1-d1d1-d1d1d1d1d1d1"
    org_id = "a0a0a0a0-a0a0-a0a0-a0a0-a0a0a0a0a0a0"
    asset_id = "b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2"

    await override_redis.hset(
        device_creds_key(key_hash),
        mapping={"device_id": device_id, "org_id": org_id,
                 "asset_id": asset_id, "is_active": "true"},
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Ping #2 arrives first (newer timestamp)
        await client.post(
            "/ingest",
            json={"lat": 20.0, "lng": 100.0, "timestamp": "2026-04-11T10:00:10Z"},
            headers={"x-api-key": raw_key},
        )
        # Ping #1 arrives late (older timestamp) — should be ignored for hot storage
        await client.post(
            "/ingest",
            json={"lat": 10.0, "lng": 90.0, "timestamp": "2026-04-11T10:00:00Z"},
            headers={"x-api-key": raw_key},
        )

    pos = await override_redis.hgetall(device_position_key(device_id))
    # Hot storage must still hold the newer position (ping #2)
    assert pos["lat"] == "20.0", "Older ping must not overwrite newer hot-storage position"
    assert pos["lng"] == "100.0"

    # Both pings must have been written to the stream (cold storage gets everything)
    stream_len = await override_redis.xlen(TELEMETRY_STREAM)
    assert stream_len == 2


@pytest.mark.asyncio
async def test_ingest_unknown_key(override_redis):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/ingest",
            json={"lat": 10.0, "lng": 106.0, "timestamp": "2026-04-11T10:00:00Z"},
            headers={"x-api-key": "unknown-key"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ingest_deactivated_device(override_redis):
    import hashlib
    raw_key = "deactivated-device-key"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    await override_redis.hset(
        device_creds_key(key_hash),
        mapping={"device_id": "d2d2d2d2-d2d2-d2d2-d2d2-d2d2d2d2d2d2",
                 "org_id": "a0a0a0a0-a0a0-a0a0-a0a0-a0a0a0a0a0a0",
                 "asset_id": "b3b3b3b3-b3b3-b3b3-b3b3-b3b3b3b3b3b3",
                 "is_active": "false"},
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/ingest",
            json={"lat": 10.0, "lng": 106.0, "timestamp": "2026-04-11T10:00:00Z"},
            headers={"x-api-key": raw_key},
        )
    assert response.status_code == 401
