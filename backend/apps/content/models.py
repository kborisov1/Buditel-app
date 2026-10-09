from typing import Any

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
            in_tracks_or_gates=self.pk is not None and self._in_tracks_or_gates(),
        )
        if errors:
            raise ValidationError(errors)

    def _in_tracks_or_gates(self) -> bool:
        gates = GateRequirement.objects.filter(models.Q(event=self) | models.Q(required_event=self))
        return TrackEntry.objects.filter(entry=self).exists() or gates.exists()


class Source(models.Model):
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="sources")
    citation = models.TextField()
    url = models.URLField("URL", max_length=500, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return self.citation[:80]


class EntryRelation(models.Model):
    """Symmetric link between two entries, stored as a mirrored pair of rows.

    Drives the related sidebar and non-event unlocking (scope 3.4).
    """

    from_entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="relations")
    to_entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="+")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["from_entry", "to_entry"], name="unique_relation"),
            models.CheckConstraint(
                condition=~models.Q(from_entry=models.F("to_entry")), name="no_self_relation"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.from_entry} - {self.to_entry}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk:
            old = EntryRelation.objects.filter(pk=self.pk).values_list("to_entry", flat=True)
            for old_to in old:
                if old_to != self.to_entry_id:
                    self._mirror(old_to).delete()
        super().save(*args, **kwargs)
        if not self._mirror(self.to_entry_id).exists():
            EntryRelation.objects.create(
                from_entry_id=self.to_entry_id, to_entry_id=self.from_entry_id
            )

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        self._mirror(self.to_entry_id).delete()
        return super().delete(*args, **kwargs)

    def _mirror(self, to_id: int) -> models.QuerySet["EntryRelation"]:
        return EntryRelation.objects.filter(from_entry_id=to_id, to_entry_id=self.from_entry_id)


class Image(models.Model):
    """Entry image. Shown as a gallery in position order (first is the main image) and
    inline in the body as ![[position]] (architecture 8)."""

    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="images")
    position = models.PositiveSmallIntegerField(
        default=1, help_text="Order in the gallery. Reference in the body as ![[position]]."
    )
    file = models.ImageField(upload_to="entries/", width_field="width", height_field="height")
    width = models.PositiveIntegerField(editable=False, null=True)
    height = models.PositiveIntegerField(editable=False, null=True)
    caption = models.CharField(max_length=300)
    credit = models.CharField(max_length=200, blank=True)
    license_note = models.CharField(
        max_length=200, help_text="For example: public domain, or the owner's own material."
    )

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(fields=["entry", "position"], name="unique_image_position"),
        ]

    def __str__(self) -> str:
        return self.caption


EVENTS_ONLY = {"type": Entry.Type.EVENT}


class Phase(models.Model):
    """Timeline band (scope 3.1). Bands may overlap; an event's phase follows from its date."""

    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        ordering = ["start_date", "end_date"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="phase_end_after_start",
                violation_error_message="The end date must not be before the start date.",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Track(models.Model):
    """Unlock track (scope 3.2). Events unlock strictly in position order within a track."""

    class Kind(models.TextChoices):
        REGULAR = "regular"
        OPENING = "opening", "Opening (other tracks start after it)"
        FINALE = "finale", "Finale (unlocks after the threshold in every track)"

    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.REGULAR)
    position = models.PositiveSmallIntegerField(unique=True, help_text="Display order.")

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["kind"],
                condition=models.Q(kind__in=["opening", "finale"]),
                name="one_opening_one_finale_track",
                violation_error_message="There can be only one opening and one finale track.",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class TrackEntry(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="items")
    entry = models.ForeignKey(
        Entry,
        on_delete=models.CASCADE,
        related_name="track_items",
        limit_choices_to=EVENTS_ONLY,
        verbose_name="event",
    )
    position = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = "track event"
        ordering = ["track", "position"]
        constraints = [
            models.UniqueConstraint(fields=["track", "position"], name="unique_track_position"),
            models.UniqueConstraint(fields=["track", "entry"], name="unique_track_entry"),
        ]

    def __str__(self) -> str:
        return f"{self.track} #{self.position}: {self.entry}"


class GateRequirement(models.Model):
    """Gate event (scope 3.3): `event` unlocks only after `required_event` is read."""

    event = models.ForeignKey(
        Entry,
        on_delete=models.CASCADE,
        related_name="gate_requirements",
        limit_choices_to=EVENTS_ONLY,
    )
    required_event = models.ForeignKey(
        Entry, on_delete=models.CASCADE, related_name="+", limit_choices_to=EVENTS_ONLY
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["event", "required_event"], name="unique_gate"),
            models.CheckConstraint(
                condition=~models.Q(event=models.F("required_event")),
                name="no_self_gate",
                violation_error_message="An event cannot require itself.",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.event} requires {self.required_event}"
