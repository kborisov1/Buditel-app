from django.apps import AppConfig


class ActivityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.activity"

    def ready(self) -> None:
        from . import signals  # noqa: F401
