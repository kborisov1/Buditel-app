from django.conf import settings
from django.db import models


class XpEvent(models.Model):
    """Append-only XP ledger (architecture 5). Totals and levels are derived by summing."""

    class Kind(models.TextChoices):
        QUIZ_FIRST_PASS = "quiz_first_pass"
        QUIZ_RETAKE = "quiz_retake"
        REVIEW = "review"
        PRACTICE = "practice"
        OLDER_EVENT_CHECK = "older_event_check"
        DAILY_CHALLENGE = "daily_challenge"
        DAILY_LOGIN = "daily_login"
        DAILY_GOAL_BONUS = "daily_goal_bonus"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="xp_events"
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    amount = models.PositiveIntegerField()
    local_date = models.DateField(help_text="The user's local date when the XP was earned.")
    reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "local_date"])]

    def __str__(self) -> str:
        return f"{self.user} +{self.amount} {self.kind}"
