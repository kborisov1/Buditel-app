from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.content.models import Entry

from .payloads import question_errors


class Question(models.Model):
    class Type(models.TextChoices):
        MULTIPLE_CHOICE = "multiple_choice"
        TRUE_FALSE = "true_false"
        DATE_ORDERING = "date_ordering"
        FILL_BLANK = "fill_blank", "Fill in the blank"

    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="questions")
    type = models.CharField(max_length=20, choices=Type.choices)
    prompt = models.TextField()
    payload = models.JSONField(default=dict)
    explanation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["entry", "id"]

    def __str__(self) -> str:
        return self.prompt[:80]

    def clean(self) -> None:
        payload, errors = question_errors(self.type, self.prompt, self.payload)
        if errors:
            raise ValidationError(errors)
        self.payload = payload


class QuizAttempt(models.Model):
    """One post-reading quiz (scope 4). Graded only when all answers are submitted."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts"
    )
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="quiz_attempts")
    started_at = models.DateTimeField()
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.PositiveSmallIntegerField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    xp_awarded = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["user", "entry"])]

    def __str__(self) -> str:
        return f"{self.user} - {self.entry} ({self.started_at:%Y-%m-%d})"


class QuizAttemptQuestion(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="items")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="+")
    position = models.PositiveSmallIntegerField()
    answer = models.JSONField(null=True, blank=True)
    correct = models.BooleanField(null=True, blank=True)

    class Meta:
        ordering = ["attempt", "position"]
        constraints = [
            models.UniqueConstraint(fields=["attempt", "position"], name="unique_attempt_position"),
            models.UniqueConstraint(fields=["attempt", "question"], name="unique_attempt_question"),
        ]

    def __str__(self) -> str:
        return f"{self.attempt} #{self.position}"
