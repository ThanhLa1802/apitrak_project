from django.urls import path

from apps.tracking.views import LiveMapView

urlpatterns = [
    path("map/<uuid:org_id>/live/", LiveMapView.as_view(), name="live-map"),
]
