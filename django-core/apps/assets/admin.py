from django.contrib import admin

from apps.assets.models import Asset


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ["name", "organization", "asset_type", "is_active", "created_at"]
    list_filter = ["asset_type", "is_active", "organization"]
    search_fields = ["name"]
    ordering = ["organization", "name"]
