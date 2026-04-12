import hashlib
import uuid

from django.contrib.gis.db import models as gis_models
from django.db import models

from apps.assets.models import Asset


class Device(models.Model):
    """
    Represents a physical IoT tracking device attached to an Asset.

    The raw API key is never stored. Only the SHA-256 hex digest is persisted
    so that FastAPI can authenticate devices via a pure Redis lookup without
    any Django HTTP call on the hot path.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.OneToOneField(Asset, on_delete=models.CASCADE, related_name="device")
    serial_number = models.CharField(max_length=100, unique=True)
    # SHA-256 hex digest of the raw API key. Write-only — never expose in responses.
    api_key_hash = models.CharField(max_length=64, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["serial_number"]

    def __str__(self) -> str:
        return f"Device {self.serial_number}"

    @staticmethod
    def hash_api_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode()).hexdigest()


class LocationRecord(models.Model):
    """
    Cold storage for historical device positions (PostGIS).
    Written asynchronously by the Celery `write_cold_storage` task.
    The live map NEVER queries this table — it reads from Redis Hot Storage.
    """

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="location_records")
    position = gis_models.PointField(srid=4326)  # (lng, lat)
    timestamp = models.DateTimeField(db_index=True)
    speed = models.FloatField(null=True, blank=True)
    heading = models.FloatField(null=True, blank=True)
    accuracy = models.FloatField(null=True, blank=True)
    battery = models.SmallIntegerField(null=True, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            # Composite B-tree index for time-series queries per device.
            models.Index(fields=["device", "-timestamp"], name="device_timestamp_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.device} @ {self.timestamp}"
