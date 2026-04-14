"""
Celery tasks consumed from the Redis Stream `telemetry_stream`.

Two independent consumer groups:
  - cold_write  → write_cold_storage
  - geofences   → evaluate_geofences

Both tasks are dispatched from apps/tracking/stream_consumer.py which runs an
async XREADGROUP loop inside the Channels ASGI process.
"""

import asyncio
import logging
from datetime import datetime, timezone

import redis
from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.gis.geos import MultiPolygon, Point
from django.core.cache import cache

from apps.devices.models import Device, LocationRecord
from apps.geofences.models import Geofence, GeofenceEvent
from shared.redis_keys import device_geofences_key

logger = logging.getLogger(__name__)

_GEOFENCE_CACHE_TTL = 60  # seconds


def _org_geofences_cache_key(org_id: str) -> str:
    return f"org:{org_id}:active_geofences"


def _get_active_geofences(org_id: str) -> list[tuple[str, MultiPolygon]]:
    """
    Return (id, polygon) tuples for all active geofences in an org.
    Cached in Redis for _GEOFENCE_CACHE_TTL seconds — geofences change rarely
    so a short TTL eliminates the DB hit on every telemetry event.
    Cache is invalidated immediately via signal on geofence save/delete.
    """
    cache_key = _org_geofences_cache_key(org_id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    geofences = list(
        Geofence.objects.filter(organization_id=org_id, is_active=True).values_list("id", "polygon")
    )
    data = [(str(gid), polygon) for gid, polygon in geofences]
    cache.set(cache_key, data, timeout=_GEOFENCE_CACHE_TTL)
    return data


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
def evaluate_geofences(
    device_id: str,
    org_id: str,
    lat: float,
    lng: float,
    timestamp: str | None = None,
) -> None:
    """
    Check whether a device has entered or exited any active geofence.

    Hot path: active geofence polygons are cached in Redis (TTL 60s) and
    containment is checked in Python using GEOS — avoids a DB query per event.
    Cache is invalidated immediately whenever a geofence is saved or deleted.
    Persists a GeofenceEvent row for every state transition (audit trail).
    """
    point = Point(lng, lat, srid=4326)

    # Current geofences containing this point — Python GEOS, no DB query on cache hit.
    current_ids: set[str] = {
        gid for gid, polygon in _get_active_geofences(org_id) if polygon.contains(point)
    }

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

    # Parse occurred_at from telemetry timestamp (falls back to now).
    occurred_at = datetime.now(tz=timezone.utc)
    if timestamp:
        occurred_at = datetime.fromisoformat(timestamp)
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)

    # Persist audit trail to DB.
    try:
        device_obj = Device.objects.get(id=device_id)
        all_changed = {gid: "entered" for gid in entered}
        all_changed.update({gid: "exited" for gid in exited})
        GeofenceEvent.objects.bulk_create([
            GeofenceEvent(
                geofence_id=gid,
                device=device_obj,
                event_type=event_type,
                occurred_at=occurred_at,
            )
            for gid, event_type in all_changed.items()
        ])
    except Device.DoesNotExist:
        logger.warning("evaluate_geofences: device %s not found", device_id)

    # Broadcast all events concurrently via Django Channels WebSocket layer.
    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.error("evaluate_geofences: channel layer not configured")
        return

    group_name = f"org_{org_id}_tracking"

    async def _broadcast() -> None:
        await asyncio.gather(
            *[
                channel_layer.group_send(
                    group_name,
                    {"type": "geofence_event", "event": "entered", "device_id": device_id, "geofence_id": gid},
                )
                for gid in entered
            ],
            *[
                channel_layer.group_send(
                    group_name,
                    {"type": "geofence_event", "event": "exited", "device_id": device_id, "geofence_id": gid},
                )
                for gid in exited
            ],
        )

    async_to_sync(_broadcast)()
