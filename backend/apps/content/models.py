from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models

from .rules import entry_field_errors


class Entry(models.Model):
    class Type(models.TextChoices):
        EVENT = "event"
        PERSON = "person"
        PLACE = "place"
        INSTITUTION = "institution"
        WORK = "work"
        CONCEPT = "concept"

    class DateCertainty(models.TextChoices):
        EXACT = "exact"
        APPROXIMATE = "approximate"
        ESTIMATED = "estimated"

    class Importance(models.TextChoices):
        MAJOR = "major"
        NOTABLE = "notable"
        MINOR = "minor"

    class Status(models.TextChoices):
        DRAFT = "draft"
        PUBLISHED = "published"

    type = models.CharField(max_length=16, choices=Type.choices)
    slug = models.SlugField(max_length=120, unique=True, help_text="Used in [[slug]] links.")
    title = models.CharField(max_length=200)
    summary = models.TextField()
    body_md = models.TextField("body (Markdown)", blank=True)
    event_date = models.DateField(
        null=True, blank=True, help_text="New Style (Gregorian). Best guess if not exact."
    )
    date_certainty = models.CharField(
        max_length=16, choices=DateCertainty.choices, default=DateCertainty.EXACT
    )
    date_note_old_style = models.CharField("Old Style date note", max_length=200, blank=True)
    region = models.CharField(max_length=100, blank=True)
    importance = models.CharField(
        max_length=16, choices=Importance.choices, blank=True, help_text="Events only."
    )
    year_order = models.PositiveSmallIntegerField(
        default=0, help_text="Order among events in the same year."
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "entries"
        ordering = ["event_date", "year_order", "title"]
        indexes = [
            GinIndex(fields=["title"], name="entry_title_trgm", opclasses=["gin_trgm_ops"]),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        errors = entry_field_errors(
            is_event=self.type == self.Type.EVENT,
            event_date=self.event_date,
            importance=self.importance,
        )
        if errors:
            raise ValidationError(errors)


class Source(models.Model):
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="sources")
    citation = models.TextField()
    url = models.URLField("URL", max_length=500, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return self.citation[:80]
