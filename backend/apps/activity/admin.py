from django.contrib import admin
from django.http import HttpRequest

from .models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Read-only, filterable by user, date, category and event type (scope 9)."""

    list_display = ["timestamp", "category", "event_type", "user", "details"]
    list_filter = ["category", "event_type", "user"]
    date_hierarchy = "timestamp"
    search_fields = ["event_type", "user__username", "user__email"]
    list_select_related = ["user"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return False
