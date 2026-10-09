from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.db import models
from django.forms import Field
from django.http import HttpRequest
from django.urls import reverse

from .models import Entry, Source
from .widgets import MarkdownPreviewWidget


class SourceInline(admin.TabularInline):  # type: ignore[type-arg]
    model = Source
    extra = 1
    fields = ["position", "citation", "url"]


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
    list_display = ["title", "type", "event_date", "year_order", "importance", "region", "status"]
    list_filter = ["type", "status", "importance", "region"]
    search_fields = ["title", "slug", "summary"]
    prepopulated_fields = {"slug": ["title"]}
    inlines = [SourceInline]
    fieldsets = [
        (None, {"fields": ["type", "title", "slug", "status"]}),
        ("Text", {"fields": ["summary", "body_md"]}),
        (
            "Date",
            {"fields": ["event_date", "date_certainty", "date_note_old_style", "year_order"]},
        ),
        ("Classification", {"fields": ["region", "importance"]}),
    ]

    def formfield_for_dbfield(
        self, db_field: models.Field[Any, Any], request: HttpRequest, **kwargs: Any
    ) -> Field | None:
        if db_field.name == "body_md":
            kwargs["widget"] = MarkdownPreviewWidget(links=preview_links())
        return super().formfield_for_dbfield(db_field, request, **kwargs)
