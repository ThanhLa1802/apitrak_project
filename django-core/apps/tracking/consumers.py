"""
Django Channels WebSocket consumer for live asset tracking.

Clients connect to:  ws://<host>/ws/tracking/<org_id>/?token=<jwt>

On connect the JWT is validated and the client is added to the Channels
group `org_{org_id}_tracking`.  The stream consumer (stream_consumer.py)
publishes messages to this group which are forwarded here to the client.
"""

import json
import logging

import jwt
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

logger = logging.getLogger(__name__)


class TrackingConsumer(AsyncWebsocketConsumer):
    async def connect(self) -> None:
        org_id = self.scope["url_route"]["kwargs"]["org_id"]
        token = self._extract_token()

        if not self._validate_token(token, org_id):
            await self.close(code=4001)
            return

        self.group_name = f"org_{org_id}_tracking"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.debug("WS connected: group=%s channel=%s", self.group_name, self.channel_name)

    async def disconnect(self, close_code: int) -> None:
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data: str = "", bytes_data: bytes = b"") -> None:
        # Clients may send filter preferences in the future; no-op for now.
        pass

    # ── Handlers for messages sent by the stream consumer ──────────────────

    async def location_update(self, event: dict) -> None:
        """Forward a device position update to the connected WebSocket client."""
        await self.send(text_data=json.dumps({"type": "location_update", **event}))

    async def geofence_event(self, event: dict) -> None:
        """Forward a geofence entry/exit event to the connected WebSocket client."""
        await self.send(text_data=json.dumps({"type": "geofence_event", **event}))

    # ── Internal helpers ────────────────────────────────────────────────────

    def _extract_token(self) -> str | None:
        query_string = self.scope.get("query_string", b"").decode()
        for part in query_string.split("&"):
            if part.startswith("token="):
                return part[len("token="):]
        return None

    def _validate_token(self, token: str | None, org_id: str) -> bool:
        if not token:
            return False
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            # Token must carry the org_id claim matching the URL parameter.
            return str(payload.get("org_id")) == str(org_id)
        except jwt.PyJWTError as exc:
            logger.warning("WS JWT validation failed: %s", exc)
            return False
