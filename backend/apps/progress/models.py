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


class QuestionState(models.Model):
    """Spaced-repetition state of a question the user has missed (scope 5, architecture 6.3).

    Created on the first miss. Box 0 to 4 maps to the review intervals.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="question_states"
    )
    question = models.ForeignKey(
        "quizzes.Question", on_delete=models.CASCADE, related_name="states"
    )
    box = models.PositiveSmallIntegerField(default=0)
    due_date = models.DateField()
    miss_count = models.PositiveIntegerField(default=0)
    last_answered_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "question"], name="unique_question_state"),
        ]
        indexes = [models.Index(fields=["user", "due_date"])]

    def __str__(self) -> str:
        return f"{self.user} - question {self.question_id}: box {self.box}"


class OlderEventCheck(models.Model):
    """Short check on older read events after every third completed entry (scope 4.1).

    `milestone` is the completed-entries count it belongs to (3, 6, ...). A check created
    with no questions counts as skipped.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="older_event_checks"
    )
    milestone = models.PositiveIntegerField()
    created_at = models.DateTimeField()
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.PositiveSmallIntegerField(null=True, blank=True)
    xp_awarded = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "milestone"], name="unique_check_milestone"),
        ]

    def __str__(self) -> str:
        return f"{self.user} - check at {self.milestone}"


class OlderEventCheckQuestion(models.Model):
    older_check = models.ForeignKey(OlderEventCheck, on_delete=models.CASCADE, related_name="items")
    question = models.ForeignKey("quizzes.Question", on_delete=models.CASCADE, related_name="+")
    position = models.PositiveSmallIntegerField()
    answer = models.JSONField(null=True, blank=True)
    correct = models.BooleanField(null=True, blank=True)

    class Meta:
        ordering = ["older_check", "position"]
        constraints = [
            models.UniqueConstraint(
                fields=["older_check", "position"], name="unique_check_position"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.older_check} #{self.position}"
