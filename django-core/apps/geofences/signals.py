from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.geofences.models import Geofence


def _invalidate_geofence_cache(org_id: str) -> None:
    cache.delete(f"org:{org_id}:active_geofences")


@receiver(post_save, sender=Geofence)
def on_geofence_save(sender, instance: Geofence, **kwargs) -> None:
    _invalidate_geofence_cache(str(instance.organization_id))


@receiver(post_delete, sender=Geofence)
def on_geofence_delete(sender, instance: Geofence, **kwargs) -> None:
    _invalidate_geofence_cache(str(instance.organization_id))
