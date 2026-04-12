from django.urls import path, include
from rest_framework import serializers as drf_serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.routers import DefaultRouter
from rest_framework.viewsets import ModelViewSet

from apps.devices.models import Device
from apps.devices.views import AssetTrackView


class DeviceSerializer(drf_serializers.ModelSerializer):
    api_key = drf_serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Device
        fields = ["id", "asset", "serial_number", "is_active", "created_at", "api_key"]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        if self.instance is None and not attrs.get("api_key"):
            raise drf_serializers.ValidationError(
                {"api_key": "This field is required when creating a device."}
            )
        return attrs

    def create(self, validated_data):
        raw_key = validated_data.pop("api_key")
        validated_data["api_key_hash"] = Device.hash_api_key(raw_key)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        raw_key = validated_data.pop("api_key", None)
        if raw_key:
            validated_data["api_key_hash"] = Device.hash_api_key(raw_key)
        return super().update(instance, validated_data)


class DeviceViewSet(ModelViewSet):
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]
    queryset = Device.objects.select_related("asset")


router = DefaultRouter()
router.register(r"devices", DeviceViewSet, basename="device")

urlpatterns = [
    path("track/", AssetTrackView.as_view(), name="asset-track"),
    path("", include(router.urls)),
]
