from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.content.models import Entry, Track, TrackEntry
from apps.progress.models import (
    EntryProgress,
    OlderEventCheck,
    OlderEventCheckQuestion,
)
from apps.quizzes.models import Question, QuizAttempt, QuizAttemptQuestion

NOW = datetime(2026, 3, 10, 9, tzinfo=UTC)


@pytest.fixture
def user(db: None, monkeypatch: pytest.MonkeyPatch) -> User:
    monkeypatch.setattr("apps.core.clock.now", lambda user=None: NOW)
    return User.objects.create_user("learner", email="learner@example.com", password="pw")


@pytest.fixture
def client(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


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


def _question(entry: Entry) -> Question:
    return Question.objects.create(
        entry=entry, type="true_false", prompt="?", payload={"answer": True}, explanation="x"
    )


def _attempt(user: User, entry: Entry, minutes: int, score: int, passed: bool | None) -> None:
    at = NOW - timedelta(minutes=minutes)
    attempt = QuizAttempt.objects.create(
        user=user,
        entry=entry,
        started_at=at,
        submitted_at=at if passed is not None else None,
        score=score if passed is not None else None,
        passed=passed,
        xp_awarded=50 if passed else 0,
    )
    for position in range(1, 6):
        QuizAttemptQuestion.objects.create(
            attempt=attempt, question=_question(entry), position=position
        )


def test_profile_basics(client: Client) -> None:
    data = client.get("/api/profile").json()
    assert data["email"] == "learner@example.com"
    assert data["level"]["title"] == "peasant"
    assert data["level"]["total_xp"] == 0  # a new account starts at 0 XP (scope 6.1)
    assert data["streak"]["current"] == 1
    assert data["history"] == []


def test_track_progress(client: Client, user: User) -> None:
    opening = Track.objects.get(kind=Track.Kind.OPENING)
    a, b = _event("a"), _event("b")
    TrackEntry.objects.create(track=opening, entry=a)
    TrackEntry.objects.create(track=opening, entry=b)
    TrackEntry.objects.create(track=opening, entry=_event("draft", False))
    EntryProgress.objects.create(
        user=user, entry=a, state="read", finished_reading_at=NOW, passed_at=NOW
    )
    tracks = client.get("/api/profile").json()["tracks"]
    assert [t["name"] for t in tracks] == list(Track.objects.values_list("name", flat=True))
    first: dict[str, Any] = tracks[0]
    assert (first["kind"], first["read"], first["total"]) == ("opening", 1, 2)
    assert all(t["total"] == 0 for t in tracks[1:])


def test_history_newest_first(client: Client, user: User) -> None:
    entry = _event("a")
    _attempt(user, entry, minutes=30, score=3, passed=False)
    _attempt(user, entry, minutes=10, score=5, passed=True)
    _attempt(user, entry, minutes=5, score=0, passed=None)  # not submitted
    _attempt(User.objects.create_user("other", password="pw"), entry, 1, 5, True)
    check = OlderEventCheck.objects.create(
        user=user,
        milestone=3,
        created_at=NOW,
        submitted_at=NOW - timedelta(minutes=20),
        score=2,
        xp_awarded=6,
    )
    for position in (1, 2, 3):
        OlderEventCheckQuestion.objects.create(
            older_check=check, question=_question(entry), position=position
        )
    OlderEventCheck.objects.create(  # skipped: no questions
        user=user, milestone=6, created_at=NOW, submitted_at=NOW, score=0
    )

    history = client.get("/api/profile").json()["history"]
    assert [(h["kind"], h["score"], h["total"], h["passed"]) for h in history] == [
        ("quiz", 5, 5, True),
        ("check", 2, 3, None),
        ("quiz", 3, 5, False),
    ]
    assert history[0]["entry"] == {"slug": "a", "title": "Title a"}
    assert history[0]["xp_awarded"] == 50
    assert history[1]["entry"] is None


def test_history_query_count_does_not_grow(
    client: Client, user: User, django_assert_max_num_queries: Any
) -> None:
    entry = _event("a")
    for minutes in range(20):
        _attempt(user, entry, minutes=minutes, score=4, passed=True)
    client.get("/api/profile")  # the day's first request also records the login
    with django_assert_max_num_queries(15):
        assert len(client.get("/api/profile").json()["history"]) == 20
