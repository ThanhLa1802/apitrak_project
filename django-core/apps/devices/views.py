from rest_framework.generics import ListAPIView
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from apps.devices.models import LocationRecord


class LocationRecordSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = LocationRecord
        geo_field = "position"
        fields = ["id", "device", "timestamp", "speed", "heading", "accuracy", "battery"]


class TimestampCursorPagination(CursorPagination):
    ordering = "-timestamp"
    page_size = 100


class AssetTrackView(ListAPIView):
    """
    Cursor-paginated historical track for a device.
    Query params: ?device=<uuid>&from=<iso>&to=<iso>
    Used for reports and replay — NOT the live map.
    """

    serializer_class = LocationRecordSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = TimestampCursorPagination

    def get_queryset(self):
        qs = LocationRecord.objects.select_related("device__asset__organization")
        device_id = self.request.query_params.get("device")
        from_ts = self.request.query_params.get("from")
        to_ts = self.request.query_params.get("to")

        if device_id:
            qs = qs.filter(device_id=device_id)
        if from_ts:
            qs = qs.filter(timestamp__gte=from_ts)
        if to_ts:
            qs = qs.filter(timestamp__lte=to_ts)

        return qs
