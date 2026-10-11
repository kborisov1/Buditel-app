from datetime import date
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.content.models import Entry, Track, TrackEntry

LOCKED_KEYS = {"locked", "id", "slug", "type", "title", "event_date"}


@pytest.fixture
def user(db: None) -> User:
    return User.objects.create_user("learner", password="pw")


@pytest.fixture
def client(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


def _entry(slug: str, title: str, published: bool = True, **fields: Any) -> Entry:
    return Entry.objects.create(
        type=fields.pop("type", Entry.Type.PERSON),
        slug=slug,
        title=title,
        summary=f"Summary {slug}",
        status=Entry.Status.PUBLISHED if published else Entry.Status.DRAFT,
        **fields,
    )


def _titles(client: Client, q: str) -> list[str]:
    response = client.get("/api/search", {"q": q})
    assert response.status_code == 200
    return [item["title"] for item in response.json()]


@pytest.fixture
def entries(db: None) -> None:
    _entry("april", "Априлското въстание")
    _entry("prep", "Подготовка на Априлското въстание")
    _entry("botev", "Христо Ботев")
    _entry("hilendar", "Хилендарски манастир")
    _entry("draft", "Априлско чернова", published=False)


def test_requires_login(db: None) -> None:
    assert Client().get("/api/search", {"q": "Ботев"}).status_code == 401


def test_prefix_before_contains(client: Client, entries: None) -> None:
    assert _titles(client, "априлското") == [
        "Априлското въстание",
        "Подготовка на Априлското въстание",
    ]


def test_case_and_spacing_ignored(client: Client, entries: None) -> None:
    assert _titles(client, "  ХРИСТО   ботев ") == ["Христо Ботев"]


def test_typo_still_matches(client: Client, entries: None) -> None:
    assert set(_titles(client, "въстане")) == {
        "Априлското въстание",
        "Подготовка на Априлското въстание",
    }
    assert _titles(client, "Хилендарскии") == ["Хилендарски манастир"]


def test_unrelated_and_drafts_excluded(client: Client, entries: None) -> None:
    assert "Хилендарски манастир" not in _titles(client, "Ботев")
    assert "Априлско чернова" not in _titles(client, "Априлско")


@pytest.mark.parametrize("q", ["", " ", "а"])
def test_too_short_query(client: Client, entries: None, q: str) -> None:
    assert _titles(client, q) == []


def test_limit(client: Client) -> None:
    for i in range(25):
        _entry(f"e{i}", f"Читалище {i}")
    assert len(_titles(client, "Читалище")) == 20


def test_locked_results_are_title_only(client: Client, user: User) -> None:
    opening = Track.objects.get(kind=Track.Kind.OPENING)
    for position, slug in enumerate(["first", "second"], start=1):
        event = _entry(
            slug,
            f"Събитие {slug}",
            type=Entry.Type.EVENT,
            event_date=date(1800, 1, position),
            importance=Entry.Importance.MAJOR,
            body_md="Secret body",
        )
        TrackEntry.objects.create(track=opening, entry=event, position=position)
    response = client.get("/api/search", {"q": "Събитие"})
    first, second = response.json()
    assert (first["locked"], first["summary"], first["progress"]) == (False, "Summary first", None)
    assert set(second) == LOCKED_KEYS
    assert "Summary second" not in response.content.decode()
    assert "Secret body" not in response.content.decode()
