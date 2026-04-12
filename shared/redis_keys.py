"""
Shared Redis key schema for Apitrak.
Both fastapi-ingestion and django-core install this package and use these
functions to build Redis key names, preventing schema drift between services.
"""

from uuid import UUID


# ── Credential cache ─────────────────────────────────────────────────────────

def device_creds_key(api_key_hash: str) -> str:
    """Hash → Hash{device_id, org_id, asset_id, is_active}. Writer: Django signal."""
    return f"device_creds:{api_key_hash}"


# ── Hot Storage ───────────────────────────────────────────────────────────────

def device_position_key(device_id: str | UUID) -> str:
    """Hash{lat, lng, ts, speed, heading, accuracy}. Writer: FastAPI ingest."""
    return f"device:{device_id}:position"


def device_geofences_key(device_id: str | UUID) -> str:
    """Set{geofence_uuid, ...} — current containment state. Writer: Celery."""
    return f"device:{device_id}:geofences"


# ── Org index ─────────────────────────────────────────────────────────────────

def org_device_ids_key(org_id: str | UUID) -> str:
    """Set{device_uuid, ...}. Writer: Django Device.post_save signal."""
    return f"org:{org_id}:device_ids"


# ── Redis Streams ─────────────────────────────────────────────────────────────

TELEMETRY_STREAM = "telemetry_stream"

# Consumer group names — both services must agree on these.
WS_BROADCAST_GROUP = "ws_broadcast"
COLD_WRITE_GROUP = "cold_write"

# Stream field names
STREAM_FIELD_DEVICE_ID = "device_id"
STREAM_FIELD_ORG_ID = "org_id"
STREAM_FIELD_LAT = "lat"
STREAM_FIELD_LNG = "lng"
STREAM_FIELD_TIMESTAMP = "ts"
STREAM_FIELD_SPEED = "speed"
STREAM_FIELD_HEADING = "heading"
STREAM_FIELD_ACCURACY = "accuracy"
STREAM_FIELD_BATTERY = "battery"

# TTL: how long a device's last-known position is retained in hot storage.
# 3600 = 1 hour; devices disappear from the live map after 1 hour of silence.
POSITION_TTL_SECONDS = 3600
