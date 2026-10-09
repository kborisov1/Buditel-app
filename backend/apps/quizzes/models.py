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
