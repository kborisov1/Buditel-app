from django.contrib import admin
from django.http import HttpRequest

from .app_settings import SPECS
from .models import AppSetting


@admin.register(AppSetting)
class AppSettingAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["key", "value", "help"]

    @admin.display(description="description")
    def help(self, obj: AppSetting) -> str:
        spec = SPECS.get(obj.key)
        return spec.help if spec else ""

    def get_readonly_fields(self, request: HttpRequest, obj: AppSetting | None = None) -> list[str]:
        return ["key", "help"] if obj else ["help"]
