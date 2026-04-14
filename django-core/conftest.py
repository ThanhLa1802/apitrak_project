import hashlib
import uuid

import pytest
from django.contrib.gis.geos import MultiPolygon, Polygon

from apps.assets.models import Asset
from apps.devices.models import Device
from apps.geofences.models import Geofence
from apps.organizations.models import Organization


@pytest.fixture
def organization():
    return Organization.objects.create(name="Test Org", slug="test-org")


@pytest.fixture
def asset(organization):
    return Asset.objects.create(
        organization=organization,
        name="Test Asset",
        asset_type="vehicle",
    )


@pytest.fixture
def device_factory(asset):
    def _make(**kwargs):
        raw_key = kwargs.pop("api_key", str(uuid.uuid4()))
        defaults = {
            "asset": asset,
            "serial_number": str(uuid.uuid4())[:12],
            "api_key_hash": hashlib.sha256(raw_key.encode()).hexdigest(),
            "is_active": True,
        }
        defaults.update(kwargs)
        return Device.objects.create(**defaults)

    return _make


@pytest.fixture
def geofence_factory(organization):
    def _make(**kwargs):
        defaults = {
            "organization": organization,
            "name": "Test Geofence",
            "polygon": MultiPolygon(Polygon.from_bbox((104, 20, 106, 22))),
            "is_active": True,
        }
        defaults.update(kwargs)
        return Geofence.objects.create(**defaults)

    return _make
