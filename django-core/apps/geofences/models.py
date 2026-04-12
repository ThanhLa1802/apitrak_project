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
