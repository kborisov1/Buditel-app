"""Unlock-graph check for the admin (scope 3.4, architecture 9).

Simulates a learner who reads everything as soon as it unlocks, using the real unlock
engine, so anything never reached is unreachable for every learner. Also finds dependency
cycles and the usual authoring slips.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from apps.content.models import Entry, GateRequirement, Track

from .unlock import UnlockGraph, load_graph, unlocked_ids


def reachable(graph: UnlockGraph) -> set[int]:
    read: set[int] = set()
    while True:
        unlocked = unlocked_ids(graph, read)
        if unlocked <= read:
            return read
        read |= unlocked


def dependency_edges(graph: UnlockGraph) -> set[tuple[int, int]]:
    """(before, after) pairs: track order, gates, and the opening track's last event before
    the first event of every other track."""
    edges: set[tuple[int, int]] = set()
    opening_last = [t.events[-1] for t in graph.tracks if t.kind == Track.Kind.OPENING and t.events]
    for track in graph.tracks:
        order = graph.unlock_order(track)
        edges |= set(zip(order, order[1:], strict=False))
        if track.kind != Track.Kind.OPENING and order:
            edges |= {(last, order[0]) for last in opening_last}
    for event, required in graph.gates.items():
        edges |= {(r, event) for r in required}
    return {(a, b) for a, b in edges if a != b}


def cycles(nodes: set[int], edges: set[tuple[int, int]]) -> list[list[int]]:
    """Strongly connected groups with more than one node (Tarjan)."""
    succ: dict[int, list[int]] = defaultdict(list)
    for a, b in sorted(edges):
        succ[a].append(b)
    index: dict[int, int] = {}
    low: dict[int, int] = {}
    stack: list[int] = []
    on_stack: set[int] = set()
    found: list[list[int]] = []

    def visit(v: int) -> None:
        index[v] = low[v] = len(index)
        stack.append(v)
        on_stack.add(v)
        for w in succ[v]:
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            group = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                group.append(w)
                if w == v:
                    break
            if len(group) > 1:
                found.append(sorted(group))

    for v in sorted(nodes):
        if v not in index:
            visit(v)
    return found


@dataclass(frozen=True)
class Issue:
    entry_id: int
    problem: str
    blocking: bool = True  # False: worth a look, but the entry is still reachable


@dataclass
class GraphReport:
    graph: UnlockGraph
    titles: dict[int, str]
    reachable: set[int]
    edges: set[tuple[int, int]]
    cycles: list[list[int]]
    issues: list[Issue] = field(default_factory=list)
    track_names: dict[int, str] = field(default_factory=dict)


def analyse(graph: UnlockGraph, titles: dict[int, str]) -> GraphReport:
    edges = dependency_edges(graph)
    report = GraphReport(graph, titles, reachable(graph), edges, cycles(set(graph.events), edges))
    in_cycle = {e for group in report.cycles for e in group}
    in_track = {e for t in graph.tracks for e in t.events}
    preds: dict[int, set[int]] = defaultdict(set)
    for a, b in edges:
        preds[b].add(a)

    def name(entry_id: int) -> str:
        return titles.get(entry_id, f"#{entry_id}")

    for e in sorted(graph.events, key=name):
        if e not in in_track:
            report.issues.append(
                Issue(e, "In no track: it unlocks through its gates only.", blocking=False)
            )
        if e in report.reachable:
            continue
        if e in in_cycle:
            problem = "Part of a dependency cycle."
        elif blockers := sorted(p for p in preds[e] if p not in report.reachable):
            problem = "Waits for unreachable: " + ", ".join(name(p) for p in blockers) + "."
        elif any(
            t.kind == Track.Kind.FINALE and graph.unlock_order(t)[:1] == (e,) for t in graph.tracks
        ):
            problem = "The finale threshold can never be met."
        else:
            problem = "Never unlocks."
        report.issues.append(Issue(e, problem))

    for e in sorted(graph.others, key=name):
        if e in report.reachable:
            continue
        if not graph.links.get(e):
            report.issues.append(Issue(e, "Not linked to any published event."))
        else:
            report.issues.append(Issue(e, "All linked events are unreachable."))
    return report


def build_report() -> GraphReport:
    graph = load_graph()
    titles = dict(
        Entry.objects.filter(pk__in=graph.events | graph.others).values_list("id", "title")
    )
    report = analyse(graph, titles)
    report.track_names = dict(Track.objects.values_list("id", "name"))
    ignored = GateRequirement.objects.filter(
        event_id__in=graph.events, required_event__status=Entry.Status.DRAFT
    ).values_list("event_id", "required_event__title")
    for event_id, draft_title in ignored:
        report.issues.append(
            Issue(
                event_id,
                f"Gate on draft “{draft_title}” is ignored until it is published.",
                blocking=False,
            )
        )
    return report
