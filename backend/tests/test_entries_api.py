import io
from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from PIL import Image as PILImage

from apps.content.library import body_link_slugs
from apps.content.models import Entry, EntryRelation, Image, Phase, Source, Track, TrackEntry
from apps.progress.models import EntryProgress

READ_AT = datetime(2026, 1, 1, 12, tzinfo=UTC)
LOCKED_KEYS = {"locked", "id", "slug", "type", "title", "event_date"}


def _entry(
    slug: str,
    type: str = Entry.Type.EVENT,
    *,
    published: bool = True,
    on: date = date(1800, 1, 1),
    **fields: Any,
) -> Entry:
    values: dict[str, Any] = {
        "type": type,
        "slug": slug,
        "title": f"Title {slug}",
        "summary": f"Summary {slug}",
        "body_md": f"Secret body of {slug}",
        "status": Entry.Status.PUBLISHED if published else Entry.Status.DRAFT,
    }
    if type == Entry.Type.EVENT:
        values |= {"event_date": on, "importance": Entry.Importance.MAJOR}
    return Entry.objects.create(**(values | fields))


def _place(track: Track, *entries: Entry) -> None:
    for position, entry in enumerate(entries, start=1):
        TrackEntry.objects.create(track=track, entry=entry, position=position)


def _read(user: User, *entries: Entry) -> None:
    for entry in entries:
        EntryProgress.objects.create(
            user=user,
            entry=entry,
            state=EntryProgress.State.READ,
            finished_reading_at=READ_AT,
            passed_at=READ_AT,
        )


@pytest.fixture
def user(db: None) -> User:
    return User.objects.create_user("learner", password="pw")


@pytest.fixture
def client(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def opening(db: None) -> Track:
    return Track.objects.get(kind=Track.Kind.OPENING)


@pytest.fixture
def regular(db: None) -> Track:
    return Track.objects.filter(kind=Track.Kind.REGULAR).first()  # type: ignore[return-value]


def _slugs(response: Any) -> list[str]:
    return [item["slug"] for item in response.json()]


def test_requires_login(db: None) -> None:
    assert Client().get("/api/entries").status_code == 401


# List


def test_list_shows_locked_entries_as_title_only(client: Client, opening: Track) -> None:
    first, second = _entry("first"), _entry("second")
    _entry("draft", published=False)
    _place(opening, first, second)

    items = {item["slug"]: item for item in client.get("/api/entries").json()}
    assert set(items) == {"first", "second"}
    assert items["first"]["locked"] is False
    assert items["first"]["summary"] == "Summary first"
    assert items["first"]["progress"] is None
    assert set(items["second"]) == LOCKED_KEYS
    assert items["second"]["locked"] is True


def test_list_includes_progress_state(client: Client, user: User, opening: Track) -> None:
    first = _entry("first")
    _place(opening, first)
    _read(user, first)
    (item,) = client.get("/api/entries").json()
    assert item["progress"] == "read"


def test_list_never_contains_locked_details(client: Client, opening: Track) -> None:
    _place(opening, _entry("first"), _entry("second"))
    content = client.get("/api/entries").content.decode()
    assert "Summary second" not in content
    assert "Secret body" not in content


def test_filter_by_type_region_and_title(client: Client) -> None:
    _entry("sofia-event", region="Sofia")
    _entry("plovdiv-event", region="Plovdiv")
    _entry("paisiy", Entry.Type.PERSON, title="Паисий Хилендарски")
    assert _slugs(client.get("/api/entries?type=person")) == ["paisiy"]
    assert _slugs(client.get("/api/entries?region=sofia")) == ["sofia-event"]
    assert _slugs(client.get("/api/entries?q=хилендар")) == ["paisiy"]


def test_filter_by_track_matches_linked_non_events(
    client: Client, opening: Track, regular: Track
) -> None:
    in_track, elsewhere = _entry("in-track"), _entry("elsewhere")
    _place(regular, in_track)
    _place(opening, elsewhere)
    person = _entry("person", Entry.Type.PERSON)
    EntryRelation.objects.create(from_entry=person, to_entry=in_track)
    _entry("unlinked", Entry.Type.PERSON)

    slugs = _slugs(client.get(f"/api/entries?track={regular.pk}"))
    assert sorted(slugs) == ["in-track", "person"]  # locked entries match too


def test_filter_by_phase_matches_linked_non_events(client: Client) -> None:
    phase = Phase.objects.create(
        name="Test", start_date=date(1840, 1, 1), end_date=date(1850, 1, 1)
    )
    inside, outside = _entry("inside", on=date(1845, 1, 1)), _entry("outside")
    person, other = _entry("person", Entry.Type.PERSON), _entry("other", Entry.Type.PERSON)
    EntryRelation.objects.create(from_entry=person, to_entry=inside)
    EntryRelation.objects.create(from_entry=other, to_entry=outside)
    draft = _entry("draft", published=False, on=date(1845, 1, 1))
    EntryRelation.objects.create(from_entry=other, to_entry=draft)

    assert sorted(_slugs(client.get(f"/api/entries?phase={phase.pk}"))) == ["inside", "person"]
    assert client.get("/api/entries?phase=999999").json() == []


def test_filter_matches_each_entry_once(client: Client) -> None:
    phase = Phase.objects.create(
        name="Test", start_date=date(1840, 1, 1), end_date=date(1850, 1, 1)
    )
    person = _entry("person", Entry.Type.PERSON)
    for slug in ["a", "b"]:
        EntryRelation.objects.create(from_entry=person, to_entry=_entry(slug, on=date(1845, 1, 1)))
    assert _slugs(client.get(f"/api/entries?phase={phase.pk}&type=person")) == ["person"]


# Detail


def test_locked_detail_has_no_body(client: Client, opening: Track) -> None:
    first, second = _entry("first"), _entry("second")
    _place(opening, first, second)
    response = client.get("/api/entries/second")
    assert response.status_code == 200
    assert set(response.json()) == LOCKED_KEYS
    assert "Secret body" not in response.content.decode()
    assert "Summary second" not in response.content.decode()


@pytest.mark.parametrize("slug", ["missing", "draft"])
def test_unknown_or_draft_detail_is_404(client: Client, slug: str) -> None:
    _entry("draft", published=False)
    assert client.get(f"/api/entries/{slug}").status_code == 404


@pytest.fixture
def media(tmp_path: Path) -> Iterator[Path]:
    with override_settings(MEDIA_ROOT=tmp_path):
        yield tmp_path


def _png() -> SimpleUploadedFile:
    buffer = io.BytesIO()
    PILImage.new("RGB", (40, 30), "brown").save(buffer, format="PNG")
    return SimpleUploadedFile("p.png", buffer.getvalue(), content_type="image/png")


def test_unlocked_detail(client: Client, user: User, opening: Track, media: Path) -> None:
    Phase.objects.create(name="Test band", start_date=date(1790, 1, 1), end_date=date(1810, 1, 1))
    first, second = _entry("first"), _entry("second")
    _place(opening, first, second)
    _read(user, first)
    _entry("hidden", published=False)
    person = _entry("person", Entry.Type.PERSON)
    EntryRelation.objects.create(from_entry=second, to_entry=first)
    EntryRelation.objects.create(from_entry=second, to_entry=person)
    second.body_md = "See [[first]], [[person|him]], [[hidden]] and ![[1]]."
    second.save()
    Source.objects.create(entry=second, citation="Book", url="https://example.com")
    Image.objects.create(entry=second, position=1, file=_png(), caption="Map", license_note="PD")

    data = client.get("/api/entries/second").json()
    assert data["locked"] is False
    assert data["body_md"].startswith("See [[first]]")
    assert data["progress"] is None
    assert data["tracks"] == [opening.name]
    assert "Test band" in data["phases"]
    assert data["sources"] == [{"citation": "Book", "url": "https://example.com"}]
    (image,) = data["images"]
    assert (image["position"], image["width"], image["height"]) == (1, 40, 30)
    assert image["src"].startswith("/media/")
    related = {r["slug"]: r["locked"] for r in data["related"]}
    assert related == {"first": False, "person": True}
    assert data["links"] == {
        "first": {"title": "Title first", "locked": False},
        "person": {"title": "Title person", "locked": True},
    }


def test_body_link_slugs_skip_images() -> None:
    assert body_link_slugs("[[a]] [[ b |label]] ![[2]] [[c|x]]") == {"a", "b", "c"}


# Finished reading


def test_finished_reading_starts_progress(
    client: Client, user: User, opening: Track, monkeypatch: pytest.MonkeyPatch
) -> None:
    _place(opening, _entry("first"))
    monkeypatch.setattr("apps.core.clock.now", lambda user=None: READ_AT)
    response = client.post("/api/entries/first/finished-reading")
    assert response.status_code == 200
    assert response.json() == {"state": "in_progress"}
    progress = EntryProgress.objects.get(user=user)
    assert progress.finished_reading_at == READ_AT
    assert client.get("/api/entries/first").json()["progress"] == "in_progress"


def test_finished_reading_keeps_read_state(client: Client, user: User, opening: Track) -> None:
    first = _entry("first")
    _place(opening, first)
    _read(user, first)
    assert client.post("/api/entries/first/finished-reading").json() == {"state": "read"}


def test_finished_reading_locked_entry_is_forbidden(
    client: Client, user: User, opening: Track
) -> None:
    _place(opening, _entry("first"), _entry("second"))
    assert client.post("/api/entries/second/finished-reading").status_code == 403
    assert not EntryProgress.objects.filter(user=user).exists()


def test_finished_reading_draft_is_404(client: Client) -> None:
    _entry("draft", published=False)
    assert client.post("/api/entries/draft/finished-reading").status_code == 404


def test_finished_reading_requires_csrf(user: User, opening: Track) -> None:
    _place(opening, _entry("first"))
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    assert client.post("/api/entries/first/finished-reading").status_code == 403
