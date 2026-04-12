import uuid
from django.db import models
from apps.organizations.models import Organization


class AssetType(models.TextChoices):
    VEHICLE = "vehicle", "Vehicle"
    CONTAINER = "container", "Container"
    PERSON = "person", "Person"
    EQUIPMENT = "equipment", "Equipment"
    OTHER = "other", "Other"


class Asset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="assets"
    )
    name = models.CharField(max_length=255)
    asset_type = models.CharField(
        max_length=20, choices=AssetType.choices, default=AssetType.OTHER
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.organization})"
