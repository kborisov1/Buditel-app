"""Unlock engine (scope 3, architecture 6.1).

`unlocked_ids` is a pure function over an `UnlockGraph` and the set of read entries, so the
rules are testable without a database. `load_graph` builds the graph from published content
only: draft entries are never unlocked, and draft events are skipped in track order, gates,
links and the finale count.
"""

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field

from django.contrib.auth.models import User

from apps.content.models import Entry, EntryRelation, GateRequirement, Track, TrackEntry
from apps.core.app_settings import get_setting

from .models import EntryProgress


@dataclass(frozen=True)
class TrackOrder:
    kind: str
    events: tuple[int, ...]


@dataclass(frozen=True)
class UnlockGraph:
    events: frozenset[int]
    others: frozenset[int]
    tracks: tuple[TrackOrder, ...]
    gates: Mapping[int, frozenset[int]] = field(default_factory=dict)
    links: Mapping[int, frozenset[int]] = field(default_factory=dict)
    finale_percentage: int = 80


def unlocked_ids(graph: UnlockGraph, read: set[int]) -> set[int]:
    """IDs of entries the user may open, given the IDs of entries they have read."""
    opening_done = all(set(t.events) <= read for t in graph.tracks if t.kind == Track.Kind.OPENING)
    finale_reached = all(
        _read_count(t, read) >= _threshold(len(t.events), graph.finale_percentage)
        for t in graph.tracks
        if t.kind != Track.Kind.FINALE
    )

    blocked: set[int] = set()
    for track in graph.tracks:
        for i, event in enumerate(track.events):
            if i > 0:
                allowed = track.events[i - 1] in read
            elif track.kind == Track.Kind.OPENING:
                allowed = True
            elif track.kind == Track.Kind.FINALE:
                allowed = opening_done and finale_reached
            else:
                allowed = opening_done
            if not allowed:
                blocked.add(event)

    unlocked = {e for e in graph.events - blocked if graph.gates.get(e, frozenset()) <= read}
    unlocked |= {e for e in graph.others if graph.links.get(e, frozenset()) & read}
    # A read entry stays readable after the author reorders tracks or adds gates.
    unlocked |= read & (graph.events | graph.others)
    return unlocked


def _read_count(track: TrackOrder, read: set[int]) -> int:
    return sum(1 for e in track.events if e in read)


def _threshold(event_count: int, percentage: int) -> int:
    """Events needed in a track for the finale: percentage of the count, rounded up."""
    return -(-event_count * percentage // 100)


def load_graph() -> UnlockGraph:
    published = Entry.objects.filter(status=Entry.Status.PUBLISHED)
    events: set[int] = set()
    others: set[int] = set()
    for entry_id, entry_type in published.values_list("id", "type"):
        (events if entry_type == Entry.Type.EVENT else others).add(entry_id)

    track_events: dict[int, list[int]] = defaultdict(list)
    kinds: dict[int, str] = {}
    rows = (
        TrackEntry.objects.filter(entry_id__in=events)
        .order_by("track__position", "position")
        .values_list("track_id", "track__kind", "entry_id")
    )
    for track_id, kind, entry_id in rows:
        kinds[track_id] = kind
        track_events[track_id].append(entry_id)
    tracks = tuple(TrackOrder(kinds[t], tuple(ids)) for t, ids in track_events.items())

    gates: dict[int, set[int]] = defaultdict(set)
    gate_rows = GateRequirement.objects.filter(
        event_id__in=events, required_event_id__in=events
    ).values_list("event_id", "required_event_id")
    for event_id, required_id in gate_rows:
        gates[event_id].add(required_id)

    links: dict[int, set[int]] = defaultdict(set)
    link_rows = EntryRelation.objects.filter(
        from_entry_id__in=others, to_entry_id__in=events
    ).values_list("from_entry_id", "to_entry_id")
    for entry_id, event_id in link_rows:
        links[entry_id].add(event_id)

    return UnlockGraph(
        events=frozenset(events),
        others=frozenset(others),
        tracks=tracks,
        gates={k: frozenset(v) for k, v in gates.items()},
        links={k: frozenset(v) for k, v in links.items()},
        finale_percentage=get_setting("finale_percentage"),
    )


def read_entry_ids(user: User) -> set[int]:
    rows = EntryProgress.objects.filter(user=user, state=EntryProgress.State.READ)
    return set(rows.values_list("entry_id", flat=True))


def unlocked_entry_ids(user: User) -> set[int]:
    """Full unlock state for a user, computed per request (architecture 6.1)."""
    return unlocked_ids(load_graph(), read_entry_ids(user))


def is_unlocked(user: User, entry_id: int) -> bool:
    return entry_id in unlocked_entry_ids(user)
