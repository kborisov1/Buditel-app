"""Learner entry endpoints (architecture 4). Locked and unlocked entries use separate
schemas, so a locked entry's body and details are never serialized (architecture 6.1)."""

from datetime import date
from typing import Literal, cast

from django.contrib.auth.models import User
from django.http import HttpRequest
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.progress.reading import EntryLocked, finish_reading, progress_states
from apps.progress.unlock import unlocked_entry_ids

from .library import body_link_slugs, filter_entries, published_entries
from .models import Entry, Phase

router = Router(tags=["entries"])


class LockedEntryOut(Schema):
    """Title only, plus the date that the timeline shows for locked events (scope 3.4)."""

    locked: Literal[True] = True
    id: int
    slug: str
    type: str
    title: str
    event_date: date | None


class EntrySummaryOut(Schema):
    locked: Literal[False] = False
    id: int
    slug: str
    type: str
    title: str
    summary: str
    event_date: date | None
    date_certainty: str
    region: str
    importance: str
    progress: str | None


class RelatedOut(Schema):
    id: int
    slug: str
    type: str
    title: str
    locked: bool


class LinkOut(Schema):
    """A [[slug]] target in the body. Locked targets render as plain titles."""

    title: str
    locked: bool


class ImageOut(Schema):
    position: int
    src: str
    width: int | None
    height: int | None
    caption: str
    credit: str
    license_note: str


class SourceOut(Schema):
    citation: str
    url: str


class EntryDetailOut(EntrySummaryOut):
    body_md: str
    date_note_old_style: str
    tracks: list[str]
    phases: list[str]
    images: list[ImageOut]
    sources: list[SourceOut]
    related: list[RelatedOut]
    links: dict[str, LinkOut]


class ProgressOut(Schema):
    state: str


def _user(request: HttpRequest) -> User:
    return cast(User, request.user)


def _locked(entry: Entry) -> LockedEntryOut:
    return LockedEntryOut(
        id=entry.pk,
        slug=entry.slug,
        type=entry.type,
        title=entry.title,
        event_date=entry.event_date,
    )


def _summary(entry: Entry, progress: str | None) -> EntrySummaryOut:
    return EntrySummaryOut(
        id=entry.pk,
        slug=entry.slug,
        type=entry.type,
        title=entry.title,
        summary=entry.summary,
        event_date=entry.event_date,
        date_certainty=entry.date_certainty,
        region=entry.region,
        importance=entry.importance,
        progress=progress,
    )


def _get_published(slug: str) -> Entry:
    entry = published_entries().filter(slug=slug).first()
    if entry is None:
        raise HttpError(404, "Not found")
    return entry


@router.get("/entries", response=list[EntrySummaryOut | LockedEntryOut])
def list_entries(
    request: HttpRequest,
    type: Entry.Type | None = None,
    track: int | None = None,
    phase: int | None = None,
    region: str | None = None,
    q: str | None = None,
) -> list[EntrySummaryOut | LockedEntryOut]:
    user = _user(request)
    unlocked = unlocked_entry_ids(user)
    states = progress_states(user)
    entries = filter_entries(
        published_entries(), type=type, track_id=track, phase_id=phase, region=region, query=q
    )
    return [_summary(e, states.get(e.pk)) if e.pk in unlocked else _locked(e) for e in entries]


@router.get("/entries/{slug}", response=EntryDetailOut | LockedEntryOut)
def get_entry(request: HttpRequest, slug: str) -> EntryDetailOut | LockedEntryOut:
    user = _user(request)
    entry = _get_published(slug)
    unlocked = unlocked_entry_ids(user)
    if entry.pk not in unlocked:
        return _locked(entry)

    related = [
        RelatedOut(id=t.pk, slug=t.slug, type=t.type, title=t.title, locked=t.pk not in unlocked)
        for t in published_entries().filter(relations__to_entry=entry).order_by("type", "title")
    ]
    link_targets = published_entries().filter(slug__in=body_link_slugs(entry.body_md))
    phases = []
    if entry.event_date:
        phases = list(
            Phase.objects.filter(
                start_date__lte=entry.event_date, end_date__gte=entry.event_date
            ).values_list("name", flat=True)
        )
    return EntryDetailOut(
        **_summary(entry, progress_states(user).get(entry.pk)).model_dump(),
        body_md=entry.body_md,
        date_note_old_style=entry.date_note_old_style,
        tracks=list(
            entry.track_items.order_by("track__position").values_list("track__name", flat=True)
        ),
        phases=phases,
        images=[
            ImageOut(
                position=i.position,
                src=i.file.url,
                width=i.width,
                height=i.height,
                caption=i.caption,
                credit=i.credit,
                license_note=i.license_note,
            )
            for i in entry.images.all()
        ],
        sources=[SourceOut(citation=s.citation, url=s.url) for s in entry.sources.all()],
        related=related,
        links={t.slug: LinkOut(title=t.title, locked=t.pk not in unlocked) for t in link_targets},
    )


@router.post("/entries/{slug}/finished-reading", response=ProgressOut)
def finished_reading(request: HttpRequest, slug: str) -> ProgressOut:
    try:
        progress = finish_reading(_user(request), _get_published(slug))
    except EntryLocked:
        raise HttpError(403, "Entry is locked") from None
    return ProgressOut(state=progress.state)
