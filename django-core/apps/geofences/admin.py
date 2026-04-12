from django.contrib import admin

from apps.geofences.models import Geofence


@admin.register(Geofence)
class GeofenceAdmin(admin.ModelAdmin):
    list_display = ["name", "organization", "is_active", "created_at"]
    list_filter = ["is_active", "organization"]
    search_fields = ["name"]
    ordering = ["organization", "name"]
    readonly_fields = ["id", "created_at"]
