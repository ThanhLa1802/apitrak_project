import hashlib

from fastapi import Depends, Header, HTTPException, status
from redis.asyncio import Redis

from app.redis_client import get_redis
from app.schemas import DeviceInfo
from shared.redis_keys import device_creds_key


async def get_device(
    x_api_key: str = Header(..., description="Device API key"),
    redis: Redis = Depends(get_redis),
) -> DeviceInfo:
    """
    Authenticate an IoT device using its API key.

    Hashes the inbound key with SHA-256, looks up the credential cache in
    Redis (written by Django's Device.post_save signal), and returns DeviceInfo.
    Raises HTTP 401 for unknown or deactivated devices — no Django HTTP call.
    """
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    data: dict = await redis.hgetall(device_creds_key(key_hash))

    if not data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    if data.get("is_active", "false").lower() != "true":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Device is deactivated")

    return DeviceInfo(
        device_id=data["device_id"],
        org_id=data["org_id"],
        asset_id=data["asset_id"],
    )
