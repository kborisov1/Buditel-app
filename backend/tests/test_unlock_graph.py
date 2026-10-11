from datetime import date

import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.content.graph_layout import layout
from apps.content.models import Entry, EntryRelation, GateRequirement, Track, TrackEntry
from apps.progress.graph_check import analyse, cycles, reachable
from apps.progress.unlock import TrackOrder, UnlockGraph

OPENING, REGULAR, FINALE = Track.Kind.OPENING, Track.Kind.REGULAR, Track.Kind.FINALE


def graph(*tracks: TrackOrder, extra: set[int] | None = None, **kw: object) -> UnlockGraph:
    events = {e for t in tracks for e in t.events} | (extra or set())
    return UnlockGraph(events=frozenset(events), tracks=tracks, **kw)  # type: ignore[arg-type]


def problems(g: UnlockGraph) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for issue in analyse(g, {}).issues:
        out.setdefault(issue.entry_id, []).append(issue.problem)
    return out


def test_healthy_graph_has_no_problems() -> None:
    g = graph(
        TrackOrder(OPENING, (1, 2)),
        TrackOrder(REGULAR, (10, 11)),
        TrackOrder(FINALE, (90,)),
        others=frozenset({100}),
        links={100: frozenset({10})},
        gates={11: frozenset({2})},
    )
    assert reachable(g) == {1, 2, 10, 11, 90, 100}
    assert problems(g) == {}


def test_cycle_across_tracks() -> None:
    g = graph(TrackOrder(REGULAR, (10, 20)), TrackOrder(REGULAR, (20, 10)), others=frozenset())
    assert cycles(set(g.events), {(10, 20), (20, 10)}) == [[10, 20]]
    assert problems(g) == {10: ["Part of a dependency cycle."], 20: ["Part of a dependency cycle."]}


def test_opening_event_in_another_track_is_not_a_cycle() -> None:
    g = graph(TrackOrder(OPENING, (1, 2)), TrackOrder(REGULAR, (2, 10)), others=frozenset())
    assert reachable(g) == {1, 2, 10}
    assert problems(g) == {}


def test_blocked_by_unreachable_gate_and_track_order() -> None:
    g = graph(
        TrackOrder(REGULAR, (10, 20)),
        TrackOrder(REGULAR, (20, 10)),
        TrackOrder(REGULAR, (30, 31)),
        gates={30: frozenset({10})},
        others=frozenset(),
    )
    found = problems(g)
    assert found[30] == ["Waits for unreachable: #10."]
    assert found[31] == ["Waits for unreachable: #30."]


def test_trackless_event_is_flagged_but_reachable() -> None:
    g = graph(TrackOrder(OPENING, (1,)), extra={50}, others=frozenset())
    assert 50 in reachable(g)
    assert problems(g) == {50: ["In no track: it unlocks through its gates only."]}
    assert [i.blocking for i in analyse(g, {}).issues] == [False]


def test_non_event_problems() -> None:
    g = graph(
        TrackOrder(REGULAR, (10, 20)),
        TrackOrder(REGULAR, (20, 10)),
        others=frozenset({100, 101}),
        links={101: frozenset({10})},
    )
    found = problems(g)
    assert found[100] == ["Not linked to any published event."]
    assert found[101] == ["All linked events are unreachable."]


def test_finale_threshold_never_met() -> None:
    g = graph(
        TrackOrder(OPENING, (1,)),
        TrackOrder(REGULAR, (10, 20)),
        TrackOrder(REGULAR, (20, 10)),
        TrackOrder(FINALE, (90,)),
        others=frozenset(),
    )
    assert problems(g)[90] == ["The finale threshold can never be met."]


def test_layout_places_every_event_once() -> None:
    g = graph(
        TrackOrder(OPENING, (1, 2)),
        TrackOrder(REGULAR, (10, 20)),
        TrackOrder(REGULAR, (20, 10)),
        extra={50},
        gates={50: frozenset({1})},
        others=frozenset(),
    )
    result = layout(analyse(g, {1: "А" * 40}))
    by_id = {n.entry_id: n for n in result.nodes}
    assert set(by_id) == {1, 2, 10, 20, 50}
    assert len({(n.x, n.y) for n in result.nodes}) == 5
    assert by_id[1].x < by_id[2].x < by_id[10].x
    assert (by_id[10].status, by_id[50].status, by_id[1].status) == ("cycle", "trackless", "ok")
    assert by_id[1].label.endswith("…") and len(by_id[1].label) == 26
    assert {e.kind for e in result.edges} == {"track", "gate", "opening"}


# Admin page


def _event(slug: str, published: bool = True) -> Entry:
    return Entry.objects.create(
        type=Entry.Type.EVENT,
        slug=slug,
        title=f"Title {slug}",
        summary="x",
        event_date=date(1800, 1, 1),
        importance=Entry.Importance.MAJOR,
        status=Entry.Status.PUBLISHED if published else Entry.Status.DRAFT,
    )


@pytest.fixture
def admin_client(db: None) -> Client:
    client = Client()
    client.force_login(User.objects.create_superuser("owner", "owner@example.com", "pw"))
    return client


def test_admin_page(admin_client: Client) -> None:
    opening = Track.objects.get(kind=OPENING)
    regular = Track.objects.filter(kind=REGULAR).first()
    assert regular is not None
    a, b, gated = _event("a"), _event("b"), _event("gated")
    TrackEntry.objects.create(track=opening, entry=a)
    TrackEntry.objects.create(track=regular, entry=b)
    GateRequirement.objects.create(event=gated, required_event=_event("draft", published=False))
    person = Entry.objects.create(
        type=Entry.Type.PERSON,
        slug="p",
        title="Lonely person",
        summary="x",
        status=Entry.Status.PUBLISHED,
    )
    EntryRelation.objects.create(from_entry=person, to_entry=_event("hidden", published=False))

    page = admin_client.get("/admin/content/track/unlock-graph/")
    assert page.status_code == 200
    html = page.content.decode()
    assert "<svg" in html and "Title a" in html
    assert "Lonely person" in html and "Not linked to any published event." in html
    blocking, warnings = html.split("<h2>Warnings")
    assert "Not linked to any published event." in blocking
    assert "Gate on draft “Title draft” is ignored" in warnings.split("<h2>Events</h2>")[0]
    assert "In no track" in html
    assert "Title draft" not in html.split("<h2>Events</h2>")[1]  # drafts are not drawn


def test_admin_page_link_and_access(admin_client: Client, db: None) -> None:
    changelist = admin_client.get("/admin/content/track/").content.decode()
    assert "/admin/content/track/unlock-graph/" in changelist
    learner = Client()
    learner.force_login(User.objects.create_user("learner", password="pw"))
    assert learner.get("/admin/content/track/unlock-graph/").status_code == 302
