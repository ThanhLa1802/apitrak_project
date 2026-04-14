import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from django.contrib.gis.geos import MultiPolygon, Polygon

from apps.devices.tasks import evaluate_geofences
from apps.geofences.models import GeofenceEvent


@pytest.mark.django_db
def test_evaluate_geofences_saves_entered_event(
    device_factory, geofence_factory
):
    # Arrange: device inside a geofence
    device = device_factory()
    geofence = geofence_factory(
        # Simple 1-degree square around (105, 21)
        polygon=MultiPolygon(Polygon.from_bbox((104, 20, 106, 22)))
    )

    with patch("apps.devices.tasks.redis.Redis") as mock_redis_cls:
        mock_r = MagicMock()
        mock_r.smembers.return_value = set()  # no previous state
        mock_redis_cls.from_url.return_value = mock_r
        mock_r.pipeline.return_value.__enter__ = MagicMock()
        mock_r.pipeline.return_value = MagicMock()

        with patch("apps.devices.tasks.async_to_sync"):
            evaluate_geofences(
                device_id=str(device.id),
                org_id=str(geofence.organization_id),
                lat=21.0,
                lng=105.0,
                timestamp="2026-04-14T10:00:00Z",
            )

    # Assert: GeofenceEvent was persisted
    assert GeofenceEvent.objects.filter(
        device=device,
        geofence=geofence,
        event_type="entered",
    ).exists()