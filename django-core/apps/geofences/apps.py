from django.apps import AppConfig


class GeofencesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.geofences"

    def ready(self) -> None:
        import apps.geofences.signals  # noqa: F401
