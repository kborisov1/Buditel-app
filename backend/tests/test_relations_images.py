import io
import json
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import Client, override_settings
from PIL import Image as PILImage

from apps.content.models import Entry, EntryRelation, Image
from tests.helpers import EMPTY_INLINES


def _entry(slug: str, type: str = Entry.Type.PERSON) -> Entry:
    return Entry.objects.create(type=type, slug=slug, title=slug.title(), summary="x")


def _pairs() -> set[tuple[str, str]]:
    return {(r.from_entry.slug, r.to_entry.slug) for r in EntryRelation.objects.all()}


@pytest.mark.django_db
def test_relation_is_mirrored() -> None:
    a, b = _entry("a"), _entry("b")
    EntryRelation.objects.create(from_entry=a, to_entry=b)
    assert _pairs() == {("a", "b"), ("b", "a")}


@pytest.mark.django_db
def test_changing_target_moves_mirror() -> None:
    a, b, c = _entry("a"), _entry("b"), _entry("c")
    relation = EntryRelation.objects.create(from_entry=a, to_entry=b)
    relation.to_entry = c
    relation.save()
    assert _pairs() == {("a", "c"), ("c", "a")}


@pytest.mark.django_db
def test_deleting_removes_mirror() -> None:
    a, b = _entry("a"), _entry("b")
    EntryRelation.objects.create(from_entry=a, to_entry=b)
    EntryRelation.objects.get(from_entry=b).delete()
    assert _pairs() == set()


@pytest.mark.django_db
def test_relation_to_self_rejected() -> None:
    a = _entry("a")
    with pytest.raises(IntegrityError):
        EntryRelation.objects.create(from_entry=a, to_entry=a)


@pytest.fixture
def media(tmp_path: Path) -> Iterator[Path]:
    with override_settings(MEDIA_ROOT=tmp_path):
        yield tmp_path


def _png(name: str = "p.png") -> SimpleUploadedFile:
    buffer = io.BytesIO()
    PILImage.new("RGB", (40, 30), "brown").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@pytest.mark.django_db
def test_image_records_size_and_orders_by_position(media: Path) -> None:
    entry = _entry("paisiy")
    second = Image.objects.create(entry=entry, position=2, file=_png(), caption="B")
    first = Image.objects.create(entry=entry, position=1, file=_png(), caption="A")
    assert (first.width, first.height) == (40, 30)
    assert list(entry.images.all()) == [first, second]


@pytest.mark.django_db
def test_image_position_unique_per_entry(media: Path) -> None:
    entry = _entry("paisiy")
    Image.objects.create(entry=entry, position=1, file=_png(), caption="A", license_note="PD")
    with pytest.raises(IntegrityError):
        Image.objects.create(entry=entry, position=1, file=_png(), caption="B", license_note="PD")


@pytest.fixture
def admin_client(db: None) -> Client:
    client = Client()
    client.force_login(User.objects.create_superuser("owner", "owner@example.com", "pw"))
    return client


def test_admin_relation_shows_on_both_pages(admin_client: Client) -> None:
    a, b = _entry("a"), _entry("b")
    EntryRelation.objects.create(from_entry=a, to_entry=b)
    for entry, other in [(a, b), (b, a)]:
        page = admin_client.get(f"/admin/content/entry/{entry.pk}/change/").content.decode()
        assert f'<option value="{other.pk}" selected>' in page


def test_admin_preview_gets_entry_images(admin_client: Client, media: Path) -> None:
    entry = _entry("paisiy")
    Image.objects.create(
        entry=entry, position=1, file=_png(), caption="Паисий", credit="ЦДА", license_note="PD"
    )
    page = admin_client.get(f"/admin/content/entry/{entry.pk}/change/").content.decode()
    refs = re.search(r'id="id_body_md-refs"[^>]*>(.*?)</script>', page)
    assert refs is not None
    image = json.loads(refs.group(1))["images"]["1"]
    assert image["caption"] == "Паисий"
    assert image["src"].startswith("/media/entries/")


def test_admin_rejects_non_image_upload(admin_client: Client, media: Path) -> None:
    data = {
        "type": "person",
        "title": "Паисий",
        "slug": "paisiy",
        "status": "draft",
        "summary": "x",
        "date_certainty": "exact",
        "year_order": 0,
        **EMPTY_INLINES,
        "images-TOTAL_FORMS": 1,
        "images-0-position": 1,
        "images-0-caption": "x",
        "images-0-license_note": "PD",
        "images-0-file": SimpleUploadedFile("fake.png", b"not an image", content_type="image/png"),
    }
    response = admin_client.post("/admin/content/entry/add/", data)
    assert response.status_code == 200
    assert "Upload a valid image" in response.content.decode()
    assert not Entry.objects.exists()
