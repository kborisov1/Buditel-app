"""Timeline data (scope 7.2): published events in order, plus the phase bands."""

from collections import defaultdict

from django.db.models import QuerySet

from .library import published_entries
from .models import Entry, Phase, Track, TrackEntry


def timeline_events() -> QuerySet[Entry]:
    """Events in the default entry order: year, then the author's year_order, then date."""
    return published_entries().filter(type=Entry.Type.EVENT)


def phases() -> QuerySet[Phase]:
    return Phase.objects.all()


def timeline_tracks() -> list[Track]:
    """The lanes: tracks that have at least one published event, in display order."""
    return list(
        Track.objects.filter(items__entry__in=timeline_events()).distinct().order_by("position")
    )


def track_ids_by_event() -> dict[int, list[int]]:
    """Track IDs for each published event, so every dot lands on its lane(s)."""
    result: dict[int, list[int]] = defaultdict(list)
    rows = TrackEntry.objects.filter(entry__in=timeline_events()).order_by("track__position")
    for entry_id, track_id in rows.values_list("entry_id", "track_id"):
        result[entry_id].append(track_id)
    return result
