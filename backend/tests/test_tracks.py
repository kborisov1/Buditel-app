from datetime import date

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client

from apps.content.models import Entry, GateRequirement, Phase, Track, TrackEntry
from apps.content.rules import order_ties
from apps.content.track_order import tie_warnings
from apps.core.app_settings import get_setting
from apps.core.models import AppSetting


def _entry(slug: str, type: str = Entry.Type.EVENT) -> Entry:
    fields: dict[str, object] = {"type": type, "slug": slug, "title": slug, "summary": "x"}
    if type == Entry.Type.EVENT:
        fields |= {"event_date": date(1800, 1, 1), "importance": Entry.Importance.MAJOR}
    return Entry.objects.create(**fields)


@pytest.mark.django_db
def test_seeded_phases_tracks_and_setting() -> None:
    assert Phase.objects.count() == 5
    tracks = list(Track.objects.values_list("name", "kind"))
    assert tracks[0] == ("Пробуждане", "opening")
    assert tracks[-1] == ("Финал", "finale")
    assert get_setting("finale_percentage") == 80


@pytest.mark.django_db
def test_setting_falls_back_to_default() -> None:
    AppSetting.objects.all().delete()
    assert get_setting("finale_percentage") == 80


@pytest.mark.django_db
@pytest.mark.parametrize("value", [0, 101, 80.5, "80", True])
def test_finale_percentage_validated(value: object) -> None:
    setting = AppSetting.objects.get(key="finale_percentage")
    setting.value = value
    with pytest.raises(ValidationError):
        setting.full_clean()


@pytest.mark.django_db
def test_only_one_opening_track() -> None:
    with pytest.raises(ValidationError, match="only one opening"):
        Track(name="Втори", kind=Track.Kind.OPENING, position=9).full_clean()
    Track(name="Обикновен", kind=Track.Kind.REGULAR, position=9).full_clean()


@pytest.mark.django_db
def test_phase_end_before_start_rejected() -> None:
    phase = Phase(name="x", start_date=date(1800, 1, 1), end_date=date(1799, 1, 1))
    with pytest.raises(ValidationError, match="end date"):
        phase.full_clean()


@pytest.mark.django_db
def test_track_accepts_events_only() -> None:
    track = Track.objects.get(kind=Track.Kind.OPENING)
    with pytest.raises(ValidationError):
        TrackEntry(track=track, entry=_entry("paisiy", Entry.Type.PERSON)).full_clean()
    TrackEntry(track=track, entry=_entry("istoriya")).full_clean()


@pytest.mark.django_db
def test_track_events_unique() -> None:
    track = Track.objects.get(kind=Track.Kind.OPENING)
    first = _entry("a")
    TrackEntry.objects.create(track=track, entry=first)
    TrackEntry(track=track, entry=_entry("b")).full_clean()
    with pytest.raises(ValidationError):
        TrackEntry(track=track, entry=first).full_clean()


@pytest.mark.django_db
def test_gate_rules() -> None:
    a, b = _entry("a"), _entry("b")
    GateRequirement(event=b, required_event=a).full_clean()
    with pytest.raises(ValidationError, match="cannot require itself"):
        GateRequirement(event=a, required_event=a).full_clean()
    with pytest.raises(ValidationError):
        GateRequirement(event=b, required_event=_entry("p", Entry.Type.PERSON)).full_clean()


@pytest.mark.django_db
@pytest.mark.parametrize("link", ["track", "gate"])
def test_event_in_track_or_gate_cannot_change_type(link: str) -> None:
    event = _entry("a")
    if link == "track":
        TrackEntry.objects.create(track=Track.objects.all()[0], entry=event)
    else:
        GateRequirement.objects.create(event=_entry("b"), required_event=event)
    event.type, event.importance = Entry.Type.CONCEPT, ""
    with pytest.raises(ValidationError) as info:
        event.full_clean()
    assert "type" in info.value.message_dict


# Admin


@pytest.fixture
def admin_client(db: None) -> Client:
    client = Client()
    client.force_login(User.objects.create_superuser("owner", "owner@example.com", "pw"))
    return client


def test_event_page_has_track_and_gate_inlines(admin_client: Client) -> None:
    event, person = _entry("a"), _entry("p", Entry.Type.PERSON)
    page = admin_client.get(f"/admin/content/entry/{event.pk}/change/").content.decode()
    assert 'id="track_items-group"' in page
    assert 'id="gate_requirements-group"' in page
    page = admin_client.get(f"/admin/content/entry/{person.pk}/change/").content.decode()
    assert "track_items-group" not in page


def test_track_page_lists_events_in_order(admin_client: Client) -> None:
    track = Track.objects.get(kind=Track.Kind.OPENING)
    second, first = _entry("second"), _entry("first")
    Entry.objects.filter(pk=second.pk).update(event_date=date(1801, 1, 1))
    TrackEntry.objects.create(track=track, entry=second)
    TrackEntry.objects.create(track=track, entry=first)
    page = admin_client.get(f"/admin/content/track/{track.pk}/change/").content.decode()
    assert page.index(">first<") < page.index(">second<")


def test_admin_setting_edit_validates(admin_client: Client) -> None:
    setting = AppSetting.objects.get(key="finale_percentage")
    url = f"/admin/core/appsetting/{setting.pk}/change/"
    assert admin_client.post(url, {"value": "150"}).status_code == 200
    assert admin_client.post(url, {"value": "75"}).status_code == 302
    assert get_setting("finale_percentage") == 75


def test_order_ties_only_when_date_and_year_order_match() -> None:
    day, next_day = date(1770, 1, 1), date(1770, 1, 2)
    assert order_ties([(1, day, 0), (2, day, 0), (3, next_day, 0)]) == [(1, 2)]
    assert order_ties([(1, day, 0), (2, day, 1)]) == []
    assert order_ties([(1, day, 0)]) == []


@pytest.mark.django_db
def test_tie_warnings_name_the_tied_events() -> None:
    track = Track.objects.get(kind=Track.Kind.OPENING)
    a, b, other = _entry("a"), _entry("b"), _entry("other")
    Entry.objects.filter(pk=other.pk).update(event_date=date(1801, 1, 1))
    for entry in (a, b, other):
        TrackEntry.objects.create(track=track, entry=entry)
    (warning,) = tie_warnings([track.pk])
    assert "“a” and “b”" in warning and track.name in warning
    assert tie_warnings([track.pk], entry_id=other.pk) == []
    Entry.objects.filter(pk=b.pk).update(year_order=1)
    assert tie_warnings([track.pk]) == []


def test_saving_a_track_warns_about_ties(admin_client: Client) -> None:
    track = Track.objects.get(kind=Track.Kind.OPENING)
    items = [TrackEntry.objects.create(track=track, entry=_entry(s)) for s in ("a", "b")]
    data = {
        "name": track.name,
        "kind": track.kind,
        "position": track.position,
        "items-TOTAL_FORMS": 2,
        "items-INITIAL_FORMS": 2,
        "items-MIN_NUM_FORMS": 0,
        "items-MAX_NUM_FORMS": 1000,
    }
    for i, item in enumerate(items):
        data |= {f"items-{i}-id": item.pk, f"items-{i}-track": track.pk}
        data |= {f"items-{i}-entry": item.entry_id}
    url = f"/admin/content/track/{track.pk}/change/"
    response = admin_client.post(url, data, follow=True)
    assert "share a date and a year order" in response.content.decode()
