"""
Django signals for the Device model.

On every Device save/delete this module keeps the Redis credential cache and
the org→device_ids index in sync so that:
  - FastAPI can authenticate devices without an HTTP call to Django.
  - LiveMapView can retrieve all device IDs for an org from Redis (0 SQL).
"""

import redis
from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.devices.models import Device
from shared.redis_keys import device_creds_key, org_device_ids_key


def _get_redis() -> redis.Redis:
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


@receiver(post_save, sender=Device)
def sync_device_to_redis(sender, instance: Device, **kwargs) -> None:
    """
    Write (or refresh) the credential cache entry and org device index.
    Called on create AND update — covers activation/deactivation.
    """
    r = _get_redis()
    pipe = r.pipeline()

    # Credential cache — read by FastAPI auth dependency.
    pipe.hset(
        device_creds_key(instance.api_key_hash),
        mapping={
            "device_id": str(instance.id),
            "org_id": str(instance.asset.organization_id),
            "asset_id": str(instance.asset_id),
            "is_active": "true" if instance.is_active else "false",
        },
    )

    if instance.is_active:
        # Add to the org's device set (used by LiveMapView).
        pipe.sadd(org_device_ids_key(instance.asset.organization_id), str(instance.id))
    else:
        # Remove deactivated device from the live map index immediately.
        pipe.srem(org_device_ids_key(instance.asset.organization_id), str(instance.id))

    pipe.execute()


@receiver(post_delete, sender=Device)
def remove_device_from_redis(sender, instance: Device, **kwargs) -> None:
    """Clean up Redis keys when a device is hard-deleted."""
    r = _get_redis()
    pipe = r.pipeline()
    pipe.delete(device_creds_key(instance.api_key_hash))
    pipe.srem(org_device_ids_key(instance.asset.organization_id), str(instance.id))
    pipe.execute()
