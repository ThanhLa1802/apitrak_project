"""
Hot Storage read service — used exclusively by LiveMapView.

Primary path: Redis Hashes (O(1), zero SQL).
Fallback path: latest LocationRecord from PostGIS for any device whose Redis
position key has expired (e.g. after a Redis restart or long silence beyond TTL).
"""

import logging

import redis
from django.conf import settings

from shared.redis_keys import device_position_key, org_device_ids_key

logger = logging.getLogger(__name__)


class HotStorageService:
    def __init__(self) -> None:
        self._client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

    def get_all_positions_for_org(self, org_id: str) -> list[dict]:
        """
        Return latest positions for all active devices in an organisation.

        1. SMEMBERS org:{org_id}:device_ids              — set of device UUIDs
        2. Pipeline HGETALL device:{id}:position × N     — one round-trip (zero SQL)
        3. For any device with no Redis data, fall back to the latest
           LocationRecord row in PostGIS (handles TTL expiry / Redis restarts).
        """
        device_ids: set[str] = self._client.smembers(org_device_ids_key(org_id))
        if not device_ids:
            return []

        pipe = self._client.pipeline()
        for device_id in device_ids:
            pipe.hgetall(device_position_key(device_id))
        results = pipe.execute()

        positions: list[dict] = []
        missing_device_ids: list[str] = []

        for device_id, data in zip(device_ids, results):
            if data:
                positions.append({"device_id": device_id, **data})
            else:
                missing_device_ids.append(device_id)

        # ── DB fallback ───────────────────────────────────────────────────────
        if missing_device_ids:
            positions.extend(self._fallback_from_db(missing_device_ids))

        return positions

    def _fallback_from_db(self, device_ids: list[str]) -> list[dict]:
        """
        Query PostGIS for the latest LocationRecord for each given device.
        Uses PostgreSQL DISTINCT ON for a single-query round-trip.
        Re-populates Redis so the next request is served from cache again.
        """
        # Imported here to avoid module-level circular import issues.
        from apps.devices.models import LocationRecord

        # DISTINCT ON (device_id) ORDER BY device_id, timestamp DESC
        # → one row per device, the most recent one.
        records = (
            LocationRecord.objects
            .filter(device_id__in=device_ids)
            .order_by("device_id", "-timestamp")
            .distinct("device_id")
            .only("device_id", "position", "timestamp", "speed", "heading", "accuracy", "battery")
        )

        fallback: list[dict] = []
        pipe = self._client.pipeline()

        for rec in records:
            device_id = str(rec.device_id)
            pos_fields = {
                "lat": str(rec.position.y),
                "lng": str(rec.position.x),
                "ts": rec.timestamp.isoformat(),
                "speed": str(rec.speed) if rec.speed is not None else "",
                "heading": str(rec.heading) if rec.heading is not None else "",
                "accuracy": str(rec.accuracy) if rec.accuracy is not None else "",
            }
            fallback.append({"device_id": device_id, **pos_fields})

            # Re-seed Redis so subsequent calls are cache hits again.
            from shared.redis_keys import POSITION_TTL_SECONDS
            pos_key = device_position_key(device_id)
            pipe.hset(pos_key, mapping=pos_fields)
            pipe.expire(pos_key, POSITION_TTL_SECONDS)

        try:
            pipe.execute()
        except Exception:
            logger.warning("hot_storage: failed to re-seed Redis from DB fallback", exc_info=True)

        if fallback:
            logger.debug(
                "hot_storage: served %d device(s) from DB fallback for org positions",
                len(fallback),
            )

        return fallback
