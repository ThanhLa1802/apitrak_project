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

# Lua script: atomically update hot-storage only when the incoming timestamp
# is strictly newer than whatever is already stored.
# ISO-8601 strings with the same timezone are lexicographically comparable,
# so a plain string comparison is correct and avoids any datetime parsing in Lua.
#
# KEYS[1] = pos_key  (e.g. "device:{uuid}:position")
# ARGV[1] = ttl      (seconds, as string)
# ARGV[2] = incoming timestamp (ISO-8601)
# ARGV[3..] = flat field/value pairs for HSET
_HSET_IF_NEWER_SCRIPT = """
local current_ts = redis.call('HGET', KEYS[1], 'timestamp')
if (not current_ts) or (ARGV[2] > current_ts) then
    local fields = {}
    for i = 3, #ARGV do
        fields[#fields + 1] = ARGV[i]
    end
    redis.call('HSET', KEYS[1], unpack(fields))
    redis.call('EXPIRE', KEYS[1], ARGV[1])
    return 1
end
return 0
"""


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_telemetry(
    payload: TelemetryPayload,
    device: DeviceInfo = Depends(get_device),
    redis: Redis = Depends(get_redis),
) -> Response:
    """
    Receive a telemetry event from an IoT device.

    1. EVAL  _HSET_IF_NEWER_SCRIPT — atomically update Hot Storage only if
             the incoming timestamp is newer than the stored one (guards against
             out-of-order delivery overwriting a more recent position).
    2. XADD  telemetry_stream      — always publish to stream so cold storage
             and geofence evaluation receive every event regardless of order.
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

    # Build flat ARGV list: ttl, timestamp, then field/value pairs
    flat_fields: list[str] = []
    for k, v in position_fields.items():
        flat_fields.extend([k, v])

    pipe = redis.pipeline()
    pipe.eval(
        _HSET_IF_NEWER_SCRIPT,
        1,           # numkeys
        pos_key,     # KEYS[1]
        str(POSITION_TTL_SECONDS),  # ARGV[1]
        ts_iso,      # ARGV[2]
        *flat_fields,               # ARGV[3..]
    )
    pipe.xadd(TELEMETRY_STREAM, stream_fields)
    await pipe.execute()

    return Response(status_code=status.HTTP_202_ACCEPTED)
