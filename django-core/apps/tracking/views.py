from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tracking.hot_storage import HotStorageService


class LiveMapView(APIView):
    """
    Returns the current position of every active device in the requesting
    user's organisation.

    Fast path:  ZERO SQL — all data served from Redis Hot Storage.
    Fallback:   If a device's Redis position has expired (TTL elapsed or Redis
                restart), the latest LocationRecord from PostGIS is used and
                Redis is re-seeded automatically for the next request.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, org_id: str) -> Response:
        service = HotStorageService()
        positions = service.get_all_positions_for_org(org_id)
        return Response({"org_id": org_id, "devices": positions})
