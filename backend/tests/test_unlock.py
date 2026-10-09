from datetime import UTC, date, datetime

import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError

from apps.content.models import Entry, EntryRelation, GateRequirement, Track, TrackEntry
from apps.core.models import AppSetting
from apps.progress.models import EntryProgress
from apps.progress.unlock import (
    TrackOrder,
    UnlockGraph,
    is_unlocked,
    load_graph,
    unlocked_entry_ids,
    unlocked_ids,
)

READ_AT = datetime(2026, 1, 1, 12, tzinfo=UTC)
OPENING, REGULAR, FINALE = Track.Kind.OPENING, Track.Kind.REGULAR, Track.Kind.FINALE


def graph(
    *tracks: TrackOrder,
    others: set[int] | None = None,
    gates: dict[int, frozenset[int]] | None = None,
    links: dict[int, frozenset[int]] | None = None,
    extra_events: set[int] | None = None,
    pct: int = 80,
) -> UnlockGraph:
    events = {e for t in tracks for e in t.events} | (extra_events or set())
    return UnlockGraph(
        events=frozenset(events),
        others=frozenset(others or set()),
        tracks=tracks,
        gates=gates or {},
        links=links or {},
        finale_percentage=pct,
    )


# Pure rules (scope 3.2-3.4, architecture 6.1)


def test_strict_order_within_track() -> None:
    g = graph(TrackOrder(OPENING, (1, 2, 3)))
    assert unlocked_ids(g, set()) == {1}
    assert unlocked_ids(g, {1}) == {1, 2}
    assert unlocked_ids(g, {1, 2, 3}) == {1, 2, 3}


def test_read_entries_stay_unlocked_after_reorder() -> None:
    g = graph(TrackOrder(OPENING, (1, 2, 3)), others={100}, gates={3: frozenset({50})})
    assert unlocked_ids(g, {3, 100}) == {1, 3, 100}


def test_read_draft_is_not_unlocked() -> None:
    g = graph(TrackOrder(OPENING, (1,)))
    assert unlocked_ids(g, {1, 99}) == {1}


def test_regular_tracks_wait_for_whole_opening_track() -> None:
    g = graph(
        TrackOrder(OPENING, (1, 2)), TrackOrder(REGULAR, (10, 11)), TrackOrder(REGULAR, (20,))
    )
    assert unlocked_ids(g, {1}) == {1, 2}
    assert unlocked_ids(g, {1, 2}) == {1, 2, 10, 20}


def test_regular_tracks_open_without_opening_track() -> None:
    g = graph(TrackOrder(REGULAR, (10, 11)))
    assert unlocked_ids(g, set()) == {10}


def test_multi_track_event_needs_every_track() -> None:
    g = graph(TrackOrder(REGULAR, (10, 30)), TrackOrder(REGULAR, (20, 21, 30)))
    assert 30 not in unlocked_ids(g, {10})
    assert 30 not in unlocked_ids(g, {10, 20})
    assert 30 in unlocked_ids(g, {10, 20, 21})


def test_gate_needs_all_required_events() -> None:
    g = graph(
        TrackOrder(REGULAR, (10, 11)),
        TrackOrder(REGULAR, (20, 21)),
        gates={11: frozenset({20, 21})},
    )
    assert 11 not in unlocked_ids(g, {10, 20})
    assert 11 in unlocked_ids(g, {10, 20, 21})


def test_gate_does_not_bypass_track_order() -> None:
    g = graph(
        TrackOrder(REGULAR, (10, 11)), TrackOrder(REGULAR, (20,)), gates={11: frozenset({20})}
    )
    assert 11 not in unlocked_ids(g, {20})


def test_event_outside_tracks_follows_gates_only() -> None:
    g = graph(TrackOrder(REGULAR, (10,)), extra_events={50, 51}, gates={51: frozenset({10})})
    assert unlocked_ids(g, set()) == {10, 50}
    assert unlocked_ids(g, {10}) == {10, 50, 51}


def test_non_event_unlocks_when_any_linked_event_read() -> None:
    g = graph(
        TrackOrder(OPENING, (1, 2)),
        others={100, 101},
        links={100: frozenset({1, 2}), 101: frozenset({2})},
    )
    assert unlocked_ids(g, set()) == {1}
    assert unlocked_ids(g, {1}) == {1, 2, 100}


def test_non_event_without_links_stays_locked() -> None:
    g = graph(TrackOrder(OPENING, (1,)), others={100})
    assert 100 not in unlocked_ids(g, {1})


def test_finale_needs_threshold_in_every_track() -> None:
    g = graph(
        TrackOrder(OPENING, (1,)),
        TrackOrder(REGULAR, tuple(range(10, 15))),  # 5 events, 80% -> 4
        TrackOrder(REGULAR, tuple(range(20, 30))),  # 10 events, 80% -> 8
        TrackOrder(FINALE, (90, 91)),
    )
    base = {1, *range(10, 14), *range(20, 27)}  # 4 of 5 and 7 of 10
    assert 90 not in unlocked_ids(g, base)
    assert unlocked_ids(g, base | {27}) >= {90}
    assert 91 not in unlocked_ids(g, base | {27})


@pytest.mark.parametrize(
    ("count", "pct", "needed"),
    [(3, 80, 3), (4, 80, 4), (6, 80, 5), (10, 80, 8), (7, 50, 4), (0, 80, 0)],
)
def test_finale_threshold_rounds_up(count: int, pct: int, needed: int) -> None:
    events = tuple(range(10, 10 + count))
    g = graph(TrackOrder(REGULAR, events), TrackOrder(FINALE, (90,)), pct=pct)
    read = set(events[:needed])
    assert 90 in unlocked_ids(g, read)
    if needed:
        assert 90 not in unlocked_ids(g, read - {events[0]})


def test_finale_counts_opening_track() -> None:
    g = graph(TrackOrder(OPENING, (1, 2)), TrackOrder(FINALE, (90,)))
    assert 90 not in unlocked_ids(g, {1})
    assert 90 in unlocked_ids(g, {1, 2})


# Loading from the database


def _entry(slug: str, type: str = Entry.Type.EVENT, published: bool = True) -> Entry:
    fields: dict[str, object] = {"type": type, "slug": slug, "title": slug, "summary": "x"}
    if type == Entry.Type.EVENT:
        fields |= {"event_date": date(1800, 1, 1), "importance": Entry.Importance.MAJOR}
    status = Entry.Status.PUBLISHED if published else Entry.Status.DRAFT
    return Entry.objects.create(status=status, **fields)


def _read(user: User, *entries: Entry) -> None:
    for entry in entries:
        EntryProgress.objects.create(
            user=user,
            entry=entry,
            state=EntryProgress.State.READ,
            finished_reading_at=READ_AT,
            passed_at=READ_AT,
        )


def _place(track: Track, *entries: Entry) -> None:
    for position, entry in enumerate(entries, start=1):
        TrackEntry.objects.create(track=track, entry=entry, position=position)


@pytest.fixture
def user(db: None) -> User:
    return User.objects.create_user("learner", password="pw")


@pytest.fixture
def opening(db: None) -> Track:
    return Track.objects.get(kind=Track.Kind.OPENING)


def test_load_graph_orders_tracks_by_position(opening: Track) -> None:
    a, b, c = _entry("a"), _entry("b"), _entry("c")
    TrackEntry.objects.create(track=opening, entry=c, position=3)
    TrackEntry.objects.create(track=opening, entry=a, position=1)
    TrackEntry.objects.create(track=opening, entry=b, position=2)
    (track,) = load_graph().tracks
    assert track == TrackOrder(OPENING, (a.pk, b.pk, c.pk))


def test_load_graph_reads_finale_setting(db: None) -> None:
    AppSetting.objects.filter(key="finale_percentage").update(value=60)
    assert load_graph().finale_percentage == 60


def test_draft_event_is_skipped_in_track_order(user: User, opening: Track) -> None:
    a, draft, c = _entry("a"), _entry("draft", published=False), _entry("c")
    _place(opening, a, draft, c)
    _read(user, a)
    assert unlocked_entry_ids(user) == {a.pk, c.pk}


def test_draft_gate_requirement_is_ignored(user: User) -> None:
    gated, draft = _entry("gated"), _entry("draft", published=False)
    GateRequirement.objects.create(event=gated, required_event=draft)
    assert is_unlocked(user, gated.pk)


def test_drafts_are_never_unlocked(user: User, opening: Track) -> None:
    draft = _entry("draft", published=False)
    _place(opening, draft)
    _read(user, draft)
    assert not is_unlocked(user, draft.pk)


def test_linked_person_unlocks_after_event_read(user: User, opening: Track) -> None:
    a, b = _entry("a"), _entry("b")
    person = _entry("paisiy", Entry.Type.PERSON)
    place = _entry("hilendar", Entry.Type.PLACE)
    _place(opening, a, b)
    EntryRelation.objects.create(from_entry=person, to_entry=b)
    EntryRelation.objects.create(from_entry=place, to_entry=person)
    _read(user, a)
    assert not is_unlocked(user, person.pk)
    _read(user, b)
    assert is_unlocked(user, person.pk)
    assert not is_unlocked(user, place.pk)  # a link to a non-event does not count


def test_in_progress_does_not_count_as_read(user: User, opening: Track) -> None:
    a, b = _entry("a"), _entry("b")
    _place(opening, a, b)
    EntryProgress.objects.create(
        user=user,
        entry=a,
        state=EntryProgress.State.IN_PROGRESS,
        finished_reading_at=READ_AT,
    )
    assert unlocked_entry_ids(user) == {a.pk}


def test_progress_is_per_user(user: User, opening: Track) -> None:
    a, b = _entry("a"), _entry("b")
    _place(opening, a, b)
    _read(User.objects.create_user("other", password="pw"), a)
    assert unlocked_entry_ids(user) == {a.pk}


def test_one_progress_row_per_user_and_entry(user: User) -> None:
    a = _entry("a")
    _read(user, a)
    with pytest.raises(IntegrityError):
        _read(user, a)
