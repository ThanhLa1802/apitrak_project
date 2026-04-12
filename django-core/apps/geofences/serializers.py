from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from apps.geofences.models import Geofence


class GeofenceSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Geofence
        geo_field = "polygon"
        fields = ["id", "organization", "name", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]
