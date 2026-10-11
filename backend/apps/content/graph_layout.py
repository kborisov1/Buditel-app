"""Layered SVG layout for the admin unlock-graph page (architecture 9)."""

from collections import defaultdict
from dataclasses import dataclass

from apps.progress.graph_check import GraphReport

NODE_W, NODE_H = 200, 40
COL_GAP, ROW_GAP, PAD = 80, 20, 20
MAX_LABEL = 26


@dataclass(frozen=True)
class Node:
    entry_id: int
    x: int
    y: int
    label: str
    title: str
    status: str  # "ok", "unreachable", "cycle" or "trackless"


@dataclass(frozen=True)
class Edge:
    path: str
    kind: str  # "track", "gate" or "opening"


@dataclass(frozen=True)
class Layout:
    nodes: list[Node]
    edges: list[Edge]
    width: int
    height: int


def _layers(
    nodes: set[int], edges: set[tuple[int, int]], groups: list[list[int]]
) -> dict[int, int]:
    """Longest-path layers, with each cycle collapsed into one node."""
    rep = {v: v for v in nodes}
    for group in groups:
        for v in group:
            rep[v] = group[0]
    preds: dict[int, set[int]] = defaultdict(set)
    for a, b in edges:
        if rep[a] != rep[b]:
            preds[rep[b]].add(rep[a])
    layer: dict[int, int] = {}

    def depth(v: int) -> int:
        if v not in layer:
            layer[v] = 0  # guards against revisiting while computing
            layer[v] = max((depth(p) + 1 for p in preds[v]), default=0)
        return layer[v]

    return {v: depth(rep[v]) for v in nodes}


def layout(report: GraphReport) -> Layout:
    graph = report.graph
    nodes = set(graph.events)
    layers = _layers(nodes, report.edges, report.cycles)
    order: dict[int, tuple[int, int]] = {}
    for t_index, track in enumerate(graph.tracks):
        for position, e in enumerate(track.events):
            order.setdefault(e, (t_index, position))

    in_cycle = {e for group in report.cycles for e in group}
    in_track = set(order)
    columns: dict[int, list[int]] = defaultdict(list)
    for e in nodes:
        columns[layers[e]].append(e)

    placed: dict[int, Node] = {}
    for col, members in columns.items():
        members.sort(key=lambda e: (order.get(e, (999, 0)), report.titles.get(e, "")))
        for row, e in enumerate(members):
            title = report.titles.get(e, f"#{e}")
            label = title if len(title) <= MAX_LABEL else title[: MAX_LABEL - 1] + "…"
            if e in in_cycle:
                status = "cycle"
            elif e not in report.reachable:
                status = "unreachable"
            elif e not in in_track:
                status = "trackless"
            else:
                status = "ok"
            placed[e] = Node(
                e,
                PAD + col * (NODE_W + COL_GAP),
                PAD + row * (NODE_H + ROW_GAP),
                label,
                title,
                status,
            )

    orders = [graph.unlock_order(t) for t in graph.tracks]
    track_pairs = {p for o in orders for p in zip(o, o[1:], strict=False)}
    gate_pairs = {(r, e) for e, required in graph.gates.items() for r in required}
    edges = []
    for a, b in sorted(report.edges):
        if a not in placed or b not in placed:
            continue
        kind = "gate" if (a, b) in gate_pairs else "track" if (a, b) in track_pairs else "opening"
        src, dst = placed[a], placed[b]
        x1, y1 = src.x + NODE_W, src.y + NODE_H // 2
        x2, y2 = dst.x, dst.y + NODE_H // 2
        bend = max(40, abs(x2 - x1) // 2)
        edges.append(Edge(f"M{x1},{y1} C{x1 + bend},{y1} {x2 - bend},{y2} {x2},{y2}", kind))

    width = PAD * 2 + (max(columns, default=0) + 1) * (NODE_W + COL_GAP)
    height = PAD * 2 + max((len(m) for m in columns.values()), default=1) * (NODE_H + ROW_GAP)
    return Layout(list(placed.values()), edges, width, height)
