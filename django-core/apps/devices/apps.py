from django.apps import AppConfig


class DevicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.devices"

    def ready(self) -> None:
        import apps.devices.signals  # noqa: F401  — registers post_save handlers
