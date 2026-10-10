import random
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.content.models import Entry, EntryRelation, Track, TrackEntry
from apps.gamification.models import XpEvent
from apps.progress.models import EntryProgress, OlderEventCheck, QuestionState
from apps.progress.older_check import draw_questions, pending_check
from apps.quizzes.models import Question

NOW = datetime(2026, 3, 10, 9, tzinfo=UTC)


@pytest.fixture
def user(db: None, monkeypatch: pytest.MonkeyPatch) -> User:
    monkeypatch.setattr("apps.core.clock.now", lambda user=None: NOW)
    return User.objects.create_user("learner", password="pw")


@pytest.fixture
def client(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


def _entry(slug: str, type: str = Entry.Type.EVENT, on: date = date(1800, 1, 1)) -> Entry:
    """A published entry outside any track (unlocked by default) with 6 questions."""
    fields: dict[str, Any] = {}
    if type == Entry.Type.EVENT:
        fields = {"event_date": on, "importance": Entry.Importance.MAJOR}
    entry = Entry.objects.create(
        type=type, slug=slug, title=slug, summary="x", status=Entry.Status.PUBLISHED, **fields
    )
    for i in range(6):
        Question.objects.create(
            entry=entry,
            type="true_false",
            prompt=f"{slug} {i}",
            payload={"answer": True},
            explanation=f"Because {slug} {i}",
        )
    return entry


def _read(user: User, *entries: Entry) -> None:
    """Mark entries read in order, each passed a minute after the previous."""
    for n, entry in enumerate(entries):
        at = NOW - timedelta(hours=1) + timedelta(minutes=n)
        EntryProgress.objects.create(
            user=user, entry=entry, state="read", finished_reading_at=at, passed_at=at
        )


def _complete(user: User, count: int) -> None:
    user.profile.completed_entries_count = count
    user.profile.save()


def _drawn_entries(user: User, seed: int = 0) -> set[str]:
    ids = draw_questions(user, random.Random(seed))
    assert len(ids) == len(set(ids))
    slugs = [q.entry.slug for q in Question.objects.filter(pk__in=ids).select_related("entry")]
    assert len(slugs) == len(set(slugs))  # one question per entry
    return set(slugs)


# Drawing (scope 4.1)


def test_draw_skips_recent_entries(user: User) -> None:
    events = [_entry(f"e{i}") for i in range(6)]
    _read(user, *events)
    for seed in range(10):
        assert _drawn_entries(user, seed) == {"e0", "e1", "e2"}


def test_draw_uses_events_only_but_counts_any_recent_entry(user: User) -> None:
    events = [_entry(f"e{i}") for i in range(4)]
    person = _entry("person", Entry.Type.PERSON)
    _read(user, *events, person)  # recent: person, e3, e2
    assert _drawn_entries(user) == {"e0", "e1"}


def test_draw_falls_back_to_all_read_events(user: User) -> None:
    _read(user, *[_entry(f"e{i}") for i in range(4)])  # only e0 is older
    assert len(_drawn_entries(user)) == 3


def test_draw_needs_two_events(user: User) -> None:
    _read(user, _entry("e0"))
    assert draw_questions(user, random.Random(0)) == []


# Pending check (architecture 6.4)


def test_no_check_before_first_milestone(user: User) -> None:
    _read(user, *[_entry(f"e{i}") for i in range(2)])
    _complete(user, 2)
    assert pending_check(user) is None


def test_check_is_created_once_and_not_stacked(user: User) -> None:
    _read(user, *[_entry(f"e{i}") for i in range(6)])
    _complete(user, 3)
    check = pending_check(user)
    assert check is not None and check.milestone == 3 and check.items.count() == 3
    assert pending_check(user) == check
    _complete(user, 7)
    later = pending_check(user)
    assert later is not None and later.milestone == 6
    assert OlderEventCheck.objects.count() == 2


def test_check_without_enough_content_is_skipped(user: User) -> None:
    _read(user, _entry("e0"))
    _complete(user, 3)
    assert pending_check(user) is None
    check = OlderEventCheck.objects.get()
    assert check.submitted_at is not None and check.items.count() == 0
    _read(user, _entry("e1"), _entry("e2"))
    assert pending_check(user) is None  # the milestone stays skipped


# Check API


@pytest.fixture
def check(user: User) -> OlderEventCheck:
    _read(user, *[_entry(f"e{i}") for i in range(6)])
    _complete(user, 3)
    check = pending_check(user)
    assert check is not None
    return check


def _submit(client: Client, check: OlderEventCheck, wrong: int = 0) -> Any:
    items = list(check.items.order_by("position"))
    answers = [{"question_id": i.question_id, "answer": n >= wrong} for n, i in enumerate(items)]
    return client.post(
        f"/api/checks/{check.pk}/submit", {"answers": answers}, content_type="application/json"
    )


def test_get_check_hides_answers(client: Client, check: OlderEventCheck) -> None:
    response = client.get(f"/api/checks/{check.pk}")
    assert len(response.json()["questions"]) == 3
    assert "Because" not in response.content.decode()


def test_submit_check_feedback_xp_and_review(
    client: Client, user: User, check: OlderEventCheck
) -> None:
    result = _submit(client, check, wrong=1).json()
    assert (result["score"], result["total"], result["xp_awarded"]) == (2, 3, 6)
    assert [r["correct"] for r in result["results"]] == [False, True, True]
    assert all(r["explanation"].startswith("Because") for r in result["results"])
    assert result["results"][0]["correct_answer"] is True
    missed = check.items.order_by("position").first()
    assert missed is not None
    assert QuestionState.objects.filter(user=user, question_id=missed.question_id).exists()
    assert XpEvent.objects.get(kind="older_event_check").amount == 6
    assert pending_check(user) is None


def test_all_wrong_gives_no_xp(client: Client, check: OlderEventCheck) -> None:
    assert _submit(client, check, wrong=3).json()["xp_awarded"] == 0
    assert not XpEvent.objects.filter(kind="older_event_check").exists()


def test_check_closed_after_submit(client: Client, check: OlderEventCheck) -> None:
    _submit(client, check)
    assert _submit(client, check).status_code == 409
    assert client.get(f"/api/checks/{check.pk}").status_code == 409


def test_check_belongs_to_user(check: OlderEventCheck) -> None:
    other = Client()
    other.force_login(User.objects.create_user("other", password="pw"))
    assert other.get(f"/api/checks/{check.pk}").status_code == 404
    assert _submit(other, check).status_code == 404


def test_check_rejects_incomplete_answers(client: Client, check: OlderEventCheck) -> None:
    first = check.items.order_by("position").first()
    assert first is not None
    body = {"answers": [{"question_id": first.question_id, "answer": True}]}
    url = f"/api/checks/{check.pk}/submit"
    assert client.post(url, body, content_type="application/json").status_code == 400


# Session queue (scope 7.1)


def test_session_order(client: Client, user: User) -> None:
    started = _entry("started", Entry.Type.PERSON)
    EntryRelation.objects.create(from_entry=started, to_entry=_entry("read-0"))
    old = [Entry.objects.get(slug="read-0"), *[_entry(f"read-{i}") for i in range(1, 3)]]
    _read(user, *old)
    EntryProgress.objects.create(
        user=user, entry=started, state="in_progress", finished_reading_at=NOW
    )
    _entry("late", on=date(1870, 1, 1))
    _entry("early", on=date(1790, 1, 1))
    _entry("middle", on=date(1830, 1, 1))
    _entry("latest", on=date(1876, 1, 1))
    QuestionState.objects.create(
        user=user, question=started.questions.all()[0], due_date=NOW.date(), last_answered_at=NOW
    )
    _complete(user, 4)  # next milestone after 2 more entries

    steps = client.get("/api/session").json()["steps"]
    assert [s["kind"] for s in steps] == ["review", "check", "entry", "entry", "check", "entry"]
    assert steps[0]["count"] == 1
    assert steps[1]["check_id"] == OlderEventCheck.objects.get(milestone=3).pk
    assert [s["slug"] for s in steps if s["kind"] == "entry"] == ["started", "early", "middle"]
    assert steps[3]["progress"] is None and steps[2]["progress"] == "in_progress"
    assert steps[4]["check_id"] is None


def test_session_skips_locked_entries(client: Client, user: User) -> None:
    track = Track.objects.get(kind=Track.Kind.OPENING)
    for position, slug in enumerate(["first", "second"], start=1):
        TrackEntry.objects.create(track=track, entry=_entry(slug), position=position)
    steps = client.get("/api/session").json()["steps"]
    assert [s.get("slug") for s in steps] == ["first"]


def test_empty_session(client: Client) -> None:
    assert client.get("/api/session").json() == {"steps": []}
