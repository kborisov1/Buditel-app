"""Profile statistics (scope 7.6): per-track progress and result history."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from django.contrib.auth.models import User
from django.db.models import Count

from apps.content.models import Entry, Track, TrackEntry
from apps.quizzes.models import QuizAttempt

from .models import OlderEventCheck
from .unlock import read_entry_ids

HISTORY_LIMIT = 50


@dataclass(frozen=True)
class TrackProgress:
    track: Track
    read: int
    total: int


def track_progress(user: User) -> list[TrackProgress]:
    """Read events out of published events, for every track in display order."""
    read = read_entry_ids(user)
    events: dict[int, list[int]] = {}
    rows = TrackEntry.objects.filter(entry__status=Entry.Status.PUBLISHED).values_list(
        "track_id", "entry_id"
    )
    for track_id, entry_id in rows:
        events.setdefault(track_id, []).append(entry_id)
    return [
        TrackProgress(
            track=track,
            read=sum(1 for e in events.get(track.pk, []) if e in read),
            total=len(events.get(track.pk, [])),
        )
        for track in Track.objects.all()
    ]


@dataclass(frozen=True)
class HistoryItem:
    kind: Literal["quiz", "check"]
    at: datetime
    score: int
    total: int
    passed: bool | None
    xp_awarded: int
    entry: Entry | None


def result_history(user: User, limit: int = HISTORY_LIMIT) -> list[HistoryItem]:
    """Submitted quizzes and answered older-event checks, newest first."""
    quizzes = (
        QuizAttempt.objects.filter(user=user, submitted_at__isnull=False)
        .select_related("entry")
        .annotate(total=Count("items"))
        .order_by("-submitted_at")[:limit]
    )
    checks = (
        OlderEventCheck.objects.filter(user=user, submitted_at__isnull=False)
        .annotate(total=Count("items"))
        .filter(total__gt=0)  # skipped checks have no questions
        .order_by("-submitted_at")[:limit]
    )
    items = [
        HistoryItem("quiz", q.submitted_at, q.score or 0, q.total, q.passed, q.xp_awarded, q.entry)
        for q in quizzes
        if q.submitted_at
    ] + [
        HistoryItem("check", c.submitted_at, c.score or 0, c.total, None, c.xp_awarded, None)
        for c in checks
        if c.submitted_at
    ]
    return sorted(items, key=lambda i: i.at, reverse=True)[:limit]
