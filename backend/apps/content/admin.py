from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.db.models import Count, QuerySet
from django.forms import ModelForm
from django.http import HttpRequest
from django.urls import reverse
from django.utils.html import format_html

from apps.quizzes.admin import QuestionInline

from .models import (
    Entry,
    EntryRelation,
    GateRequirement,
    Image,
    Phase,
    Source,
    Track,
    TrackEntry,
)
from .widgets import MarkdownPreviewWidget


class SourceInline(admin.TabularInline):  # type: ignore[type-arg]
    model = Source
    extra = 1
    fields = ["position", "citation", "url"]


class RelationInline(admin.TabularInline):  # type: ignore[type-arg]
    """Symmetric: adding B here also lists this entry on B's page (architecture 5)."""

    model = EntryRelation
    fk_name = "from_entry"
    fields = ["to_entry"]
    autocomplete_fields = ["to_entry"]
    extra = 1
    verbose_name = "related entry"
    verbose_name_plural = "related entries"


class ImageInline(admin.TabularInline):  # type: ignore[type-arg]
    model = Image
    fields = ["position", "thumbnail", "file", "caption", "credit", "license_note"]
    readonly_fields = ["thumbnail"]
    extra = 1

    @admin.display(description="preview")
    def thumbnail(self, obj: Image) -> str:
        if not obj.file:
            return ""
        return format_html('<img src="{}" style="max-height: 80px">', obj.file.url)


class EntryTrackInline(admin.TabularInline):  # type: ignore[type-arg]
    """Track membership on the event's page (scope 3.2, 9)."""

    model = TrackEntry
    fields = ["track", "position"]
    extra = 0
    verbose_name = "track"
    verbose_name_plural = "tracks (position = order within the track)"


class GateInline(admin.TabularInline):  # type: ignore[type-arg]
    """Gate event (scope 3.3): this event unlocks only after these events are read."""

    model = GateRequirement
    fk_name = "event"
    fields = ["required_event"]
    autocomplete_fields = ["required_event"]
    extra = 0
    verbose_name = "gate requirement"
    verbose_name_plural = "gate: unlocks only after these events are read"


def preview_images(entry: Entry | None) -> dict[str, dict[str, str]]:
    """The entry's saved images by position, for ![[position]] in the Markdown preview."""
    if entry is None:
        return {}
    return {
        str(image.position): {
            "src": image.file.url,
            "caption": image.caption,
            "credit": image.credit,
        }
        for image in entry.images.all()
    }


def preview_links() -> dict[str, dict[str, str | None]]:
    """All entries by slug, linking to their admin page, for the Markdown preview."""
    return {
        e["slug"]: {
            "title": e["title"],
            "href": reverse("admin:content_entry_change", args=[e["id"]]),
        }
        for e in Entry.objects.values("id", "slug", "title")
    }


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = [
        "title",
        "type",
        "event_date",
        "year_order",
        "importance",
        "region",
        "status",
        "question_count",
    ]
    list_filter = ["type", "status", "importance", "region", "track_items__track"]
    search_fields = ["title", "slug", "summary"]
    prepopulated_fields = {"slug": ["title"]}
    inlines = [RelationInline, ImageInline, SourceInline, QuestionInline]
    fieldsets = [
        (None, {"fields": ["type", "title", "slug", "status"]}),
        ("Text", {"fields": ["summary", "body_md"]}),
        (
            "Date",
            {"fields": ["event_date", "date_certainty", "date_note_old_style", "year_order"]},
        ),
        ("Classification", {"fields": ["region", "importance"]}),
    ]

    def get_inlines(self, request: HttpRequest, obj: Entry | None) -> list[Any]:
        """Tracks and gates apply to saved events only."""
        if obj is not None and obj.type == Entry.Type.EVENT:
            return [EntryTrackInline, GateInline, *self.inlines]
        return list(self.inlines)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Entry]:
        queryset: QuerySet[Entry] = super().get_queryset(request)
        return queryset.annotate(question_count=Count("questions"))

    @admin.display(description="questions", ordering="question_count")
    def question_count(self, obj: Entry) -> int:
        return int(getattr(obj, "question_count", 0))

    def get_form(
        self, request: HttpRequest, obj: Entry | None = None, change: bool = False, **kwargs: Any
    ) -> type[ModelForm[Entry]]:
        form: type[ModelForm[Entry]] = super().get_form(request, obj, change, **kwargs)
        form.base_fields["body_md"].widget = MarkdownPreviewWidget(
            links=preview_links(), images=preview_images(obj)
        )
        return form


class TrackEntryInline(admin.TabularInline):  # type: ignore[type-arg]
    model = TrackEntry
    fields = ["position", "entry"]
    autocomplete_fields = ["entry"]
    extra = 1


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["name", "kind", "position", "event_count"]
    inlines = [TrackEntryInline]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Track]:
        queryset: QuerySet[Track] = super().get_queryset(request)
        return queryset.annotate(event_count=Count("items"))

    @admin.display(description="events", ordering="event_count")
    def event_count(self, obj: Track) -> int:
        return int(getattr(obj, "event_count", 0))


@admin.register(Phase)
class PhaseAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["name", "start_date", "end_date"]
