from django.urls import re_path

from apps.tracking.consumers import TrackingConsumer

websocket_urlpatterns = [
    re_path(
        r"ws/tracking/(?P<org_id>[0-9a-f-]{36})/$",
        TrackingConsumer.as_asgi(),
    ),
]
