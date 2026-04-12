from django.contrib import admin

from apps.devices.models import Device, LocationRecord


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ["serial_number", "asset", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["serial_number"]
    ordering = ["serial_number"]
    # Never display the raw hash in any form field
    exclude = ["api_key_hash"]
    readonly_fields = ["id", "created_at"]


@admin.register(LocationRecord)
class LocationRecordAdmin(admin.ModelAdmin):
    list_display = ["device", "timestamp", "speed", "heading", "battery", "received_at"]
    list_filter = ["device"]
    search_fields = ["device__serial_number"]
    ordering = ["-timestamp"]
    readonly_fields = ["id", "received_at"]
