from django.conf import settings
from django.db import models

from apps.content.models import Entry


class EntryProgress(models.Model):
    """A user's reading state for one entry (architecture 5). No row means no progress.

    Lock state is computed by `progress.unlock`, never stored.
    """

    class State(models.TextChoices):
        IN_PROGRESS = "in_progress"
        READ = "read"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="entry_progress"
    )
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="progress")
    state = models.CharField(max_length=16, choices=State.choices)
    finished_reading_at = models.DateTimeField()
    passed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "entry progress"
        constraints = [
            models.UniqueConstraint(fields=["user", "entry"], name="unique_entry_progress"),
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.entry}: {self.state}"
