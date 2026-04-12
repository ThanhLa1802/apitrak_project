from fastapi import APIRouter, Depends, Response, status
from redis.asyncio import Redis

from app.dependencies.auth import get_device
from app.redis_client import get_redis
from app.schemas import DeviceInfo, TelemetryPayload
from shared.redis_keys import (
    POSITION_TTL_SECONDS,
    TELEMETRY_STREAM,
    device_position_key,
    STREAM_FIELD_ACCURACY,
    STREAM_FIELD_BATTERY,
    STREAM_FIELD_DEVICE_ID,
    STREAM_FIELD_HEADING,
    STREAM_FIELD_LAT,
    STREAM_FIELD_LNG,
    STREAM_FIELD_ORG_ID,
    STREAM_FIELD_SPEED,
    STREAM_FIELD_TIMESTAMP,
)

router = APIRouter()


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_telemetry(
    payload: TelemetryPayload,
    device: DeviceInfo = Depends(get_device),
    redis: Redis = Depends(get_redis),
) -> Response:
    """
    Receive a telemetry event from an IoT device.

    Fast path (single Redis round-trip via pipeline):
      1. HSET  device:{id}:position   — Hot Storage update
      2. EXPIRE device:{id}:position  — TTL = 2× ping interval
      3. XADD  telemetry_stream       — Publish for Channels + Celery consumers
    """
    pos_key = device_position_key(device.device_id)
    ts_iso = payload.timestamp.isoformat()

    position_fields: dict[str, str] = {
        STREAM_FIELD_LAT: str(payload.lat),
        STREAM_FIELD_LNG: str(payload.lng),
        STREAM_FIELD_TIMESTAMP: ts_iso,
        STREAM_FIELD_SPEED: str(payload.speed) if payload.speed is not None else "",
        STREAM_FIELD_HEADING: str(payload.heading) if payload.heading is not None else "",
        STREAM_FIELD_ACCURACY: str(payload.accuracy) if payload.accuracy is not None else "",
    }

    stream_fields: dict[str, str] = {
        STREAM_FIELD_DEVICE_ID: str(device.device_id),
        STREAM_FIELD_ORG_ID: str(device.org_id),
        **position_fields,
        STREAM_FIELD_BATTERY: str(payload.battery) if payload.battery is not None else "",
    }

    pipe = redis.pipeline()
    pipe.hset(pos_key, mapping=position_fields)
    pipe.expire(pos_key, POSITION_TTL_SECONDS)
    pipe.xadd(TELEMETRY_STREAM, stream_fields)
    await pipe.execute()

    return Response(status_code=status.HTTP_202_ACCEPTED)
