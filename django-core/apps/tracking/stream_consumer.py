"""
Async Redis Stream consumer for the `ws_broadcast` consumer group.

Reads from `telemetry_stream` and forwards each event to the appropriate
Django Channels group so connected WebSocket clients receive live updates.

This runs as a background asyncio task inside the Channels ASGI process.
It is started once from TrackingConfig.ready() and is NOT a Celery task.
"""

import asyncio
import logging

import redis.asyncio as aioredis
from channels.layers import get_channel_layer
from django.conf import settings

from shared.redis_keys import (
    COLD_WRITE_GROUP,
    TELEMETRY_STREAM,
    WS_BROADCAST_GROUP,
    STREAM_FIELD_DEVICE_ID,
    STREAM_FIELD_ORG_ID,
    STREAM_FIELD_LAT,
    STREAM_FIELD_LNG,
    STREAM_FIELD_TIMESTAMP,
    STREAM_FIELD_SPEED,
    STREAM_FIELD_HEADING,
    STREAM_FIELD_ACCURACY,
    STREAM_FIELD_BATTERY,
)

logger = logging.getLogger(__name__)

_CONSUMER_NAME = "django-channels-1"
_READ_COUNT = 50
_BLOCK_MS = 2000  # block for 2 s waiting for new messages


async def _ensure_consumer_groups(r: aioredis.Redis) -> None:
    """Create both consumer groups if they don't exist yet (idempotent)."""
    for group in (WS_BROADCAST_GROUP, COLD_WRITE_GROUP):
        try:
            await r.xgroup_create(TELEMETRY_STREAM, group, id="0", mkstream=True)
        except Exception:
            pass  # BUSYGROUP — group already exists


async def _dispatch_celery_tasks(fields: dict) -> None:
    """
    Dispatch Celery tasks for cold storage write and geofence evaluation.
    Imported here to avoid circular imports at module level.
    """
    from apps.devices.tasks import evaluate_geofences, write_cold_storage

    device_id = fields.get(STREAM_FIELD_DEVICE_ID, "")
    org_id = fields.get(STREAM_FIELD_ORG_ID, "")
    lat = float(fields.get(STREAM_FIELD_LAT, 0))
    lng = float(fields.get(STREAM_FIELD_LNG, 0))
    ts = fields.get(STREAM_FIELD_TIMESTAMP, "")
    speed_raw = fields.get(STREAM_FIELD_SPEED, "")
    heading_raw = fields.get(STREAM_FIELD_HEADING, "")
    accuracy_raw = fields.get(STREAM_FIELD_ACCURACY, "")
    battery_raw = fields.get(STREAM_FIELD_BATTERY, "")

    write_cold_storage.delay(
        device_id=device_id,
        lat=lat,
        lng=lng,
        ts=ts,
        speed=float(speed_raw) if speed_raw else None,
        heading=float(heading_raw) if heading_raw else None,
        accuracy=float(accuracy_raw) if accuracy_raw else None,
        battery=int(battery_raw) if battery_raw else None,
    )
    evaluate_geofences.delay(
        device_id=device_id,
        org_id=org_id,
        lat=lat,
        lng=lng,
    )


async def _consume_stream() -> None:
    r = aioredis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    channel_layer = get_channel_layer()

    await _ensure_consumer_groups(r)

    logger.info("TelemetryStreamConsumer started, reading from '%s'", TELEMETRY_STREAM)

    while True:
        try:
            results = await r.xreadgroup(
                groupname=WS_BROADCAST_GROUP,
                consumername=_CONSUMER_NAME,
                streams={TELEMETRY_STREAM: ">"},
                count=_READ_COUNT,
                block=_BLOCK_MS,
            )

            if not results:
                continue

            for _stream_name, messages in results:
                for msg_id, fields in messages:
                    org_id = fields.get(STREAM_FIELD_ORG_ID, "")
                    group_name = f"org_{org_id}_tracking"

                    # Broadcast to WebSocket clients.
                    await channel_layer.group_send(
                        group_name,
                        {
                            "type": "location_update",
                            "device_id": fields.get(STREAM_FIELD_DEVICE_ID),
                            "lat": fields.get(STREAM_FIELD_LAT),
                            "lng": fields.get(STREAM_FIELD_LNG),
                            "timestamp": fields.get(STREAM_FIELD_TIMESTAMP),
                            "speed": fields.get(STREAM_FIELD_SPEED),
                            "heading": fields.get(STREAM_FIELD_HEADING),
                            "battery": fields.get(STREAM_FIELD_BATTERY),
                        },
                    )

                    # Dispatch Celery tasks for cold write + geofence check.
                    await _dispatch_celery_tasks(fields)

                    # Acknowledge the message so it is not re-delivered.
                    await r.xack(TELEMETRY_STREAM, WS_BROADCAST_GROUP, msg_id)

        except asyncio.CancelledError:
            logger.info("TelemetryStreamConsumer cancelled, shutting down.")
            break
        except Exception as exc:
            logger.exception("TelemetryStreamConsumer error: %s", exc)
            await asyncio.sleep(1)  # brief back-off before retrying

    await r.aclose()


def start_stream_consumer() -> None:
    """
    Schedule the stream consumer coroutine on the running event loop (if any)
    or create a new background thread with its own loop.
    Called from TrackingConfig.ready().
    """
    import threading

    def _run_in_thread() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_consume_stream())

    thread = threading.Thread(target=_run_in_thread, daemon=True, name="telemetry-stream-consumer")
    thread.start()
