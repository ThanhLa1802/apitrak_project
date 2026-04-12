from django.apps import AppConfig


class TrackingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tracking"

    def ready(self) -> None:
        # Start the Redis Stream consumer coroutine inside the Channels
        # ASGI worker when the application boots.
        # Guard with a flag to avoid double-start in Django's auto-reloader.
        import os
        if os.environ.get("RUN_MAIN") != "true":
            from apps.tracking.stream_consumer import start_stream_consumer
            start_stream_consumer()
