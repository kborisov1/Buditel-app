"""Chronological order of events within a track (scope 2.3, 3.2)."""

from collections.abc import Iterable

from .models import Track
from .rules import order_ties


def tie_warnings(track_ids: Iterable[int], entry_id: int | None = None) -> list[str]:
    """Admin warnings for events whose order within a track falls back to the title.
    With `entry_id`, only ties involving that event are reported."""
    warnings = []
    for track in Track.objects.filter(pk__in=list(track_ids)):
        entries = [item.entry for item in track.items.select_related("entry")]
        titles = {e.pk: e.title for e in entries}
        events = [(e.pk, e.event_date, e.year_order) for e in entries]
        for a, b in order_ties(events):
            if entry_id is None or entry_id in (a, b):
                warnings.append(
                    f"“{titles[a]}” and “{titles[b]}” in {track.name} share a date and a "
                    "year order, so they are ordered by title. Set the year order to fix it."
                )
    return warnings
