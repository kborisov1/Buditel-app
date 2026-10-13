"""Unlock engine (scope 3, architecture 6.1).

`unlocked_ids` is a pure function over an `UnlockGraph` and the set of read entries, so the
rules are testable without a database. `load_graph` builds the graph from published content
only: draft entries are never unlocked, and draft events are skipped in track order, gates,
links and the finale count.
"""

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from django.contrib.auth.models import User

from apps.content.models import (
    Entry,
    EntryRelation,
    GateRequirement,
    Track,
    TrackEntry,
    chronological,
)
from apps.core.app_settings import get_setting

from .models import EntryProgress


@dataclass(frozen=True)
class TrackOrder:
    kind: str
    events: tuple[int, ...]
    track_id: int = field(default=0, compare=False)
    # Events of other regular tracks dated before this track's first event: reading them is
    # what opens a regular track (scope 3.2). Empty for the opening and finale tracks.
    before_start: frozenset[int] = frozenset()


@dataclass(frozen=True)
class UnlockGraph:
    events: frozenset[int]
    others: frozenset[int]
    tracks: tuple[TrackOrder, ...]
    gates: Mapping[int, frozenset[int]] = field(default_factory=dict)
    links: Mapping[int, frozenset[int]] = field(default_factory=dict)
    finale_percentage: int = 80

    def unlock_order(self, track: TrackOrder) -> tuple[int, ...]:
        """Events in the order `track` unlocks them. Other tracks skip opening-track events:
        those follow the opening track alone, since every other track waits for it anyway
        (architecture 6.1). Without this, an opening event in another track never unlocks."""
        if track.kind == Track.Kind.OPENING:
            return track.events
        opening = {e for t in self.tracks if t.kind == Track.Kind.OPENING for e in t.events}
        return tuple(e for e in track.events if e not in opening)


def _track_opens(graph: UnlockGraph, track: TrackOrder, read: set[int]) -> bool:
    """Whether the first event of `track` may be read (scope 3.2): the opening track is always
    open; the finale needs its threshold; a regular track needs the whole opening track and
    every earlier-dated event of the other regular tracks."""
    if track.kind == Track.Kind.OPENING:
        return True
    opening_done = all(set(t.events) <= read for t in graph.tracks if t.kind == Track.Kind.OPENING)
    if track.kind == Track.Kind.FINALE:
        finale_reached = all(
            _read_count(t, read) >= _threshold(len(t.events), graph.finale_percentage)
            for t in graph.tracks
            if t.kind != Track.Kind.FINALE
        )
        return opening_done and finale_reached
    return opening_done and track.before_start <= read


def open_track_ids(graph: UnlockGraph, read: set[int]) -> set[int]:
    """IDs of the tracks the user may start reading; tracks with no events count as open."""
    return {t.track_id for t in graph.tracks if _track_opens(graph, t, read)}


def unlocked_ids(graph: UnlockGraph, read: set[int]) -> set[int]:
    """IDs of entries the user may open, given the IDs of entries they have read."""
    blocked: set[int] = set()
    for track in graph.tracks:
        order = graph.unlock_order(track)
        opens = _track_opens(graph, track, read)
        for i, event in enumerate(order):
            allowed = order[i - 1] in read if i > 0 else opens
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
        .order_by("track__position", *chronological("entry__"), "entry_id")
        .values_list("track_id", "track__kind", "entry_id")
    )
    for track_id, kind, entry_id in rows:
        kinds[track_id] = kind
        track_events[track_id].append(entry_id)
    tracks = _with_before_start(
        tuple(TrackOrder(kinds[t], tuple(ids), t) for t, ids in track_events.items())
    )

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


def _with_before_start(tracks: tuple[TrackOrder, ...]) -> tuple[TrackOrder, ...]:
    """Fills `before_start` for regular tracks. Each track's events are already in timeline
    order and every event's rank is its place in the combined order, so "dated before" uses the
    same order as the tracks themselves (scope 2.3)."""
    ids = [e for t in tracks for e in t.events]
    rank = {e: r for r, e in enumerate(_chronological_ids(ids))}
    opening = {e for t in tracks if t.kind == Track.Kind.OPENING for e in t.events}
    result = []
    for track in tracks:
        own_order = [e for e in track.events if e not in opening]
        if track.kind != Track.Kind.REGULAR or not own_order:
            result.append(track)
            continue
        start = rank[own_order[0]]
        before = frozenset(
            e
            for other in tracks
            if other.kind == Track.Kind.REGULAR and other is not track
            for e in other.events
            if rank[e] < start and e not in opening and e not in track.events
        )
        result.append(replace(track, before_start=before))
    return tuple(result)


def _chronological_ids(ids: list[int]) -> list[int]:
    unique = list(dict.fromkeys(ids))
    ordered = (
        Entry.objects.filter(pk__in=unique)
        .order_by(*chronological(), "pk")
        .values_list("pk", flat=True)
    )
    return list(ordered)


def read_entry_ids(user: User) -> set[int]:
    rows = EntryProgress.objects.filter(user=user, state=EntryProgress.State.READ)
    return set(rows.values_list("entry_id", flat=True))


def unlocked_entry_ids(user: User) -> set[int]:
    """Full unlock state for a user, computed per request (architecture 6.1)."""
    return unlocked_ids(load_graph(), read_entry_ids(user))


def is_unlocked(user: User, entry_id: int) -> bool:
    return entry_id in unlocked_entry_ids(user)
