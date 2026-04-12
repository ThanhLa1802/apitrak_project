from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from apps.geofences.models import Geofence
from apps.geofences.serializers import GeofenceSerializer


class GeofenceViewSet(ModelViewSet):
    """
    CRUD for Geofence polygons. GeoJSON input/output via djangorestframework-gis.
    Filtered by org_id query param (e.g. ?org_id=<uuid>) or JWT auth_context.
    Pagination is disabled — returns a raw GeoJSON FeatureCollection.
    """

    serializer_class = GeofenceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = Geofence.objects.select_related("organization")
        org_id = self.request.query_params.get("org_id") or (
            self.request.auth_context.get("org_id")
            if hasattr(self.request, "auth_context")
            else None
        )
        if org_id:
            qs = qs.filter(organization_id=org_id)
        return qs
