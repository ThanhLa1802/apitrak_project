from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.geofences.views import GeofenceViewSet

router = DefaultRouter()
router.register(r"geofences", GeofenceViewSet, basename="geofence")

urlpatterns = [
    path("", include(router.urls)),
]
