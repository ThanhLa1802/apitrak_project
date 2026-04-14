import datetime

import jwt
from django.conf import settings
from django.urls import path
from rest_framework import serializers as drf_serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework.serializers import ModelSerializer
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.organizations.models import Organization


class OrganizationSerializer(ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "created_at"]
        read_only_fields = ["id", "created_at"]


class OrganizationViewSet(ModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Organization.objects.filter(members=self.request.user)


class OrgScopeTokenView(APIView):
    """
    Issue a short-lived JWT scoped to a specific organization.
    Used by WebSocket clients to authenticate against the tracking consumer.
    POST body: {"org_id": "<uuid>"}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        org_id = request.data.get("org_id")
        if not org_id:
            return Response({"detail": "org_id is required."}, status=400)
        try:
            Organization.objects.get(id=org_id, members=request.user)
        except (Organization.DoesNotExist, ValueError):
            return Response({"detail": "Organization not found."}, status=404)

        now = datetime.datetime.now(tz=datetime.timezone.utc)
        payload = {
            "org_id": str(org_id),
            "user_id": request.user.id,
            "type": "org_scope",
            "iat": int(now.timestamp()),
            "exp": int((now + datetime.timedelta(hours=8)).timestamp()),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        return Response({"token": token, "org_id": str(org_id)})


router = DefaultRouter()
router.register(r"organizations", OrganizationViewSet, basename="organization")

urlpatterns = router.urls + [
    path("token/org-scope/", OrgScopeTokenView.as_view(), name="token_org_scope"),
]
