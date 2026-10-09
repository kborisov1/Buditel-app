from django.conf import settings
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    time_zone = models.CharField(max_length=64, default="UTC")
    date_offset_days = models.IntegerField(default=0)
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    freezes_held = models.PositiveSmallIntegerField(default=0)
    last_active_local_date = models.DateField(null=True, blank=True)
    completed_entries_count = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"Profile({self.user})"
