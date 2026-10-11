from datetime import date
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.content.models import Entry, Phase, Track, TrackEntry
from apps.progress.models import EntryProgress

LOCKED_KEYS = {"locked", "id", "slug", "title", "event_date", "date_certainty", "importance"}


@pytest.fixture
def user(db: None) -> User:
    return User.objects.create_user("learner", password="pw")


@pytest.fixture
def client(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


def _entry(slug: str, on: date | None = date(1800, 1, 1), **fields: Any) -> Entry:
    values: dict[str, Any] = {
        "type": Entry.Type.EVENT,
        "slug": slug,
        "title": f"Title {slug}",
        "summary": f"Summary {slug}",
        "body_md": f"Secret body {slug}",
        "status": Entry.Status.PUBLISHED,
        "region": "Пловдив",
    }
    if fields.get("type", Entry.Type.EVENT) == Entry.Type.EVENT:
        values |= {"event_date": on, "importance": Entry.Importance.MAJOR}
    return Entry.objects.create(**(values | fields))


def test_requires_login(db: None) -> None:
    assert Client().get("/api/timeline").status_code == 401


def test_period_and_phases(client: Client) -> None:
    data = client.get("/api/timeline").json()
    assert (data["start"], data["end"]) == ("1762-01-01", "1878-12-31")
    phases = list(Phase.objects.order_by("start_date", "end_date"))
    assert [p["name"] for p in data["phases"]] == [p.name for p in phases]
    assert data["phases"][0]["start_date"] == phases[0].start_date.isoformat()


def test_events_only_in_order(client: Client) -> None:
    _entry("late", date(1876, 4, 20))
    _entry("second-same-year", date(1835, 1, 1), year_order=2)
    _entry("first-same-year", date(1835, 6, 1), year_order=1)
    _entry("draft", status=Entry.Status.DRAFT)
    _entry("person", None, type=Entry.Type.PERSON, importance="")
    slugs = [e["slug"] for e in client.get("/api/timeline").json()["events"]]
    assert slugs == ["first-same-year", "second-same-year", "late"]


def test_locked_and_unlocked_shapes(client: Client, user: User) -> None:
    opening = Track.objects.get(kind=Track.Kind.OPENING)
    first = _entry("first", date(1762, 1, 1))
    second = _entry(
        "second",
        date(1800, 1, 1),
        date_certainty=Entry.DateCertainty.APPROXIMATE,
        importance=Entry.Importance.MINOR,
    )
    TrackEntry.objects.create(track=opening, entry=first)
    TrackEntry.objects.create(track=opening, entry=second)
    EntryProgress.objects.create(
        user=user, entry=first, state="in_progress", finished_reading_at="2026-01-01T00:00Z"
    )

    response = client.get("/api/timeline")
    unlocked, locked = response.json()["events"]
    assert unlocked["locked"] is False
    assert (unlocked["summary"], unlocked["region"], unlocked["progress"]) == (
        "Summary first",
        "Пловдив",
        "in_progress",
    )
    assert set(locked) == LOCKED_KEYS
    assert (locked["date_certainty"], locked["importance"]) == ("approximate", "minor")
    content = response.content.decode()
    assert "Summary second" not in content and "Secret body" not in content
