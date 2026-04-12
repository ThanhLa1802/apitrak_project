from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ModelSerializer

from apps.assets.models import Asset


class AssetSerializer(ModelSerializer):
    class Meta:
        model = Asset
        fields = ["id", "organization", "name", "asset_type", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class AssetViewSet(ModelViewSet):
    serializer_class = AssetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Asset.objects.select_related("organization")


router = DefaultRouter()
router.register(r"assets", AssetViewSet, basename="asset")

urlpatterns = [path("", include(router.urls))]
