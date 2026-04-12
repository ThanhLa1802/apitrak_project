"""
Celery tasks consumed from the Redis Stream `telemetry_stream`.

Two independent consumer groups:
  - cold_write  → write_cold_storage
  - geofences   → evaluate_geofences

Both tasks are dispatched from apps/tracking/stream_consumer.py which runs an
async XREADGROUP loop inside the Channels ASGI process.
"""

import logging
from datetime import datetime, timezone

import redis
from celery import shared_task
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.gis.geos import Point

from apps.devices.models import Device, LocationRecord
from apps.geofences.models import Geofence
from shared.redis_keys import device_geofences_key

logger = logging.getLogger(__name__)


@shared_task(queue="cold_write", ignore_result=True)
def write_cold_storage(
    device_id: str,
    lat: float,
    lng: float,
    ts: str,
    speed: float | None,
    heading: float | None,
    accuracy: float | None,
    battery: int | None,
) -> None:
    """
    Persist a telemetry event to PostGIS (cold storage).
    Fire-and-forget — acceptable eventual consistency with Redis Hot Storage.
    """
    try:
        device = Device.objects.get(id=device_id, is_active=True)
    except Device.DoesNotExist:
        logger.warning("write_cold_storage: device %s not found or inactive", device_id)
        return

    timestamp = datetime.fromisoformat(ts)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    LocationRecord.objects.create(
        device=device,
        position=Point(lng, lat, srid=4326),  # PostGIS: (x=lng, y=lat)
        timestamp=timestamp,
        speed=speed,
        heading=heading,
        accuracy=accuracy,
        battery=battery,
    )


@shared_task(queue="geofences", ignore_result=True)
def evaluate_geofences(device_id: str, org_id: str, lat: float, lng: float) -> None:
    """
    Check whether a device has entered or exited any active geofence.

    Uses PostGIS `polygon__contains` for spatial membership test,
    diffs against the Redis Set of previously-known containment,
    then fires WebSocket events for entry/exit transitions.
    """
    point = Point(lng, lat, srid=4326)

    # Current geofences containing this point (PostGIS query).
    current_ids: set[str] = set(
        str(gid)
        for gid in Geofence.objects.filter(
            organization_id=org_id,
            is_active=True,
            polygon__contains=point,
        ).values_list("id", flat=True)
    )

    # Previous state from Redis Set.
    r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    geofences_key = device_geofences_key(device_id)
    previous_ids: set[str] = r.smembers(geofences_key)

    entered = current_ids - previous_ids
    exited = previous_ids - current_ids

    if not entered and not exited:
        return

    # Update Redis Set to reflect current containment state.
    pipe = r.pipeline()
    if current_ids:
        pipe.delete(geofences_key)
        pipe.sadd(geofences_key, *current_ids)
    else:
        pipe.delete(geofences_key)
    pipe.execute()

    # Broadcast events via Django Channels WebSocket layer.
    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.error("evaluate_geofences: channel layer not configured")
        return

    import asyncio

    loop = asyncio.new_event_loop()
    try:
        for geofence_id in entered:
            loop.run_until_complete(
                channel_layer.group_send(
                    f"org_{org_id}_tracking",
                    {
                        "type": "geofence_event",
                        "event": "entered",
                        "device_id": device_id,
                        "geofence_id": geofence_id,
                    },
                )
            )
        for geofence_id in exited:
            loop.run_until_complete(
                channel_layer.group_send(
                    f"org_{org_id}_tracking",
                    {
                        "type": "geofence_event",
                        "event": "exited",
                        "device_id": device_id,
                        "geofence_id": geofence_id,
                    },
                )
            )
    finally:
        loop.close()
