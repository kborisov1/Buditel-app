import json
import re
from datetime import date

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client

from apps.content.models import Entry, Source
from apps.content.rules import entry_field_errors


def _event(**overrides: object) -> Entry:
    fields: dict[str, object] = {
        "type": Entry.Type.EVENT,
        "slug": "istoriya",
        "title": "История славянобългарска",
        "summary": "Паисий завършва историята.",
        "event_date": date(1762, 1, 1),
        "importance": Entry.Importance.MAJOR,
        **overrides,
    }
    return Entry(**fields)


def test_event_needs_date_and_importance() -> None:
    errors = entry_field_errors(is_event=True, event_date=None, importance="")
    assert set(errors) == {"event_date", "importance"}


@pytest.mark.parametrize(
    ("day", "ok"),
    [
        (date(1761, 12, 31), False),
        (date(1762, 1, 1), True),
        (date(1878, 12, 31), True),
        (date(1879, 1, 1), False),
    ],
)
def test_event_date_within_period(day: date, ok: bool) -> None:
    errors = entry_field_errors(is_event=True, event_date=day, importance="major")
    assert ("event_date" not in errors) is ok


def test_non_event_may_be_undated_and_out_of_period() -> None:
    assert entry_field_errors(is_event=False, event_date=None, importance="") == {}
    assert entry_field_errors(is_event=False, event_date=date(1722, 1, 1), importance="") == {}


def test_non_event_rejects_importance() -> None:
    errors = entry_field_errors(is_event=False, event_date=None, importance="major")
    assert set(errors) == {"importance"}


@pytest.mark.django_db
def test_entry_clean_raises_field_errors() -> None:
    with pytest.raises(ValidationError) as info:
        _event(event_date=None).full_clean()
    assert "event_date" in info.value.message_dict


@pytest.mark.django_db
def test_sources_ordered_by_position() -> None:
    entry = _event()
    entry.save()
    Source.objects.create(entry=entry, citation="Second", position=2)
    Source.objects.create(entry=entry, citation="First", position=1)
    assert [s.citation for s in entry.sources.all()] == ["First", "Second"]


@pytest.mark.django_db
def test_title_trigram_search() -> None:
    _event().save()
    assert Entry.objects.filter(title__trigram_similar="История славянобългарски").exists()


@pytest.fixture
def admin_client(db: None) -> Client:
    client = Client()
    client.force_login(User.objects.create_superuser("owner", "owner@example.com", "pw"))
    return client


def test_admin_change_page_has_markdown_preview(admin_client: Client) -> None:
    entry = _event(body_md="Виж [[istoriya]].")
    entry.save()
    page = admin_client.get(f"/admin/content/entry/{entry.pk}/change/").content.decode()
    assert 'data-markdown-preview="id_body_md"' in page
    assert "content/admin/markdown-preview.js" in page
    links_json = re.search(r'id="id_body_md-links"[^>]*>(.*?)</script>', page)
    assert links_json is not None
    assert json.loads(links_json.group(1))["istoriya"] == {
        "title": "История славянобългарска",
        "href": f"/admin/content/entry/{entry.pk}/change/",
    }


def test_admin_add_rejects_invalid_event(admin_client: Client) -> None:
    response = admin_client.post(
        "/admin/content/entry/add/",
        {
            "type": "event",
            "title": "Без дата",
            "slug": "bez-data",
            "status": "draft",
            "summary": "x",
            "date_certainty": "exact",
            "year_order": 0,
            "sources-TOTAL_FORMS": 0,
            "sources-INITIAL_FORMS": 0,
            "questions-TOTAL_FORMS": 0,
            "questions-INITIAL_FORMS": 0,
        },
    )
    assert response.status_code == 200
    assert "Events need a date" in response.content.decode()
    assert not Entry.objects.exists()
