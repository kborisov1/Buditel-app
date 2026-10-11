from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class ActivityLog(models.Model):
    """Searchable log of user activity, content changes and errors (scope 9, architecture 10)."""

    class Category(models.TextChoices):
        USER = "user"
        CONTENT = "content"
        ERROR = "error"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity",
    )
    timestamp = models.DateTimeField(db_index=True)
    category = models.CharField(max_length=16, choices=Category.choices)
    event_type = models.CharField(max_length=64)
    details = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)

    class Meta:
        ordering = ["-timestamp", "-id"]
        indexes = [
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["event_type", "timestamp"]),
        ]

    def __str__(self) -> str:
        return f"{self.timestamp:%Y-%m-%d %H:%M} {self.category}/{self.event_type}"
