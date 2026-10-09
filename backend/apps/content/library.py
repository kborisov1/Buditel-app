"""Queries behind the learner-facing entry list and pages (scope 7.3, 7.4)."""

import re

from django.db.models import Q, QuerySet

from .models import Entry, Phase

# [[slug]] or [[slug|label]], but not ![[position]] (architecture 8).
BODY_LINK = re.compile(r"(?<!!)\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]")


def published_entries() -> QuerySet[Entry]:
    return Entry.objects.filter(status=Entry.Status.PUBLISHED)


def filter_entries(
    entries: QuerySet[Entry],
    *,
    type: str | None = None,
    track_id: int | None = None,
    phase_id: int | None = None,
    region: str | None = None,
    query: str | None = None,
) -> QuerySet[Entry]:
    """Library filters. Locked entries are matched too; callers decide what to show.

    Only events have tracks and dates, so a non-event matches a track or period through
    any published event it is linked to.
    """
    if type:
        entries = entries.filter(type=type)
    if region:
        entries = entries.filter(region__iexact=region.strip())
    if query:
        entries = entries.filter(title__icontains=query.strip())
    if track_id is not None:
        entries = entries.filter(_event_or_linked(track_items__track_id=track_id))
    if phase_id is not None:
        phase = Phase.objects.filter(pk=phase_id).first()
        if phase is None:
            return entries.none()
        entries = entries.filter(
            _event_or_linked(event_date__range=(phase.start_date, phase.end_date))
        )
    return entries.distinct()


def _event_or_linked(**lookups: object) -> Q:
    """Match events on `lookups`, and non-events through a linked published event."""
    linked = {f"relations__to_entry__{key}": value for key, value in lookups.items()}
    return Q(type=Entry.Type.EVENT, **lookups) | (
        ~Q(type=Entry.Type.EVENT)
        & Q(
            relations__to_entry__type=Entry.Type.EVENT,
            relations__to_entry__status=Entry.Status.PUBLISHED,
            **linked,
        )
    )


def body_link_slugs(body: str) -> set[str]:
    return {slug.strip() for slug in BODY_LINK.findall(body)}
