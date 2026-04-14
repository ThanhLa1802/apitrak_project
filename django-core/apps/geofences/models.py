import uuid

from django.contrib.gis.db import models as gis_models
from django.db import models

from apps.organizations.models import Organization


class Geofence(models.Model):
    """
    A named geographic area (MultiPolygon) belonging to an Organisation.
    PostGIS `polygon__contains` queries check whether a device position falls
    inside this area. These queries run only in the Celery geofence task —
    never on the live map read path.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="geofences"
    )
    name = models.CharField(max_length=255)
    polygon = gis_models.MultiPolygonField(srid=4326)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.organization})"

#create Geofence event
EVENT_CHOICES = [("entered", "Entered"), ("exited", "Exited")]

class GeofenceEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    geofence = models.ForeignKey(Geofence, on_delete=models.CASCADE, related_name="events")
    device = models.ForeignKey(
        "devices.Device", on_delete=models.CASCADE, related_name="geofence_events"
    )
    event_type = models.CharField(max_length=10, choices=EVENT_CHOICES)
    occurred_at = models.DateTimeField()   # set từ telemetry timestamp, KHÔNG auto
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["device", "-occurred_at"], name="gfev_device_time_idx"),
            models.Index(fields=["geofence", "-occurred_at"], name="gfev_fence_time_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.event_type}: device {self.device_id} @ {self.geofence.name}"