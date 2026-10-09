from django.core.exceptions import ValidationError
from django.db import models

from .app_settings import SPECS, setting_error


class AppSetting(models.Model):
    """Tunable value edited in the admin (architecture 5). Known keys live in app_settings."""

    key = models.CharField(max_length=64, unique=True, choices=[(k, k) for k in SPECS])
    value = models.JSONField()

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return self.key

    def clean(self) -> None:
        error = setting_error(self.key, self.value)
        if error:
            raise ValidationError({"value": error})
