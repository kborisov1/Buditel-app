from datetime import UTC, date, datetime
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.content.models import Entry, EntryRelation, Phase, Track, TrackEntry
from apps.gamification.models import XpEvent
from apps.progress.models import EntryProgress, QuestionState
from apps.quizzes.models import Question, QuizAttempt

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


def _entry(
    slug: str,
    type: str = Entry.Type.EVENT,
    on: date = date(1800, 1, 1),
    questions: int = 2,
    published: bool = True,
) -> Entry:
    fields: dict[str, Any] = {}
    if type == Entry.Type.EVENT:
        fields = {"event_date": on, "importance": Entry.Importance.MAJOR}
    entry = Entry.objects.create(
        type=type,
        slug=slug,
        title=slug,
        summary="x",
        status=Entry.Status.PUBLISHED if published else Entry.Status.DRAFT,
        **fields,
    )
    for i in range(questions):
        Question.objects.create(
            entry=entry,
            type="true_false",
            prompt=f"{slug} {i}",
            payload={"answer": True},
            explanation=f"Because {slug} {i}",
        )
    return entry


def _read(user: User, *entries: Entry) -> None:
    for entry in entries:
        EntryProgress.objects.create(
            user=user, entry=entry, state="read", finished_reading_at=NOW, passed_at=NOW
        )


def _prompts(response: Any) -> set[str]:
    return {q["prompt"].rsplit(" ", 1)[0] for q in response.json()["questions"]}


def test_draws_only_from_read_entries(client: Client, user: User) -> None:
    read, started = _entry("read"), _entry("started")
    _entry("unread")
    draft = _entry("draft", published=False)
    _read(user, read, draft)
    EntryProgress.objects.create(
        user=user, entry=started, state="in_progress", finished_reading_at=NOW
    )
    response = client.get("/api/practice")
    assert _prompts(response) == {"read"}
    assert "Because" not in response.content.decode()


def test_filter_by_track_and_phase(client: Client, user: User) -> None:
    track = Track.objects.filter(kind=Track.Kind.REGULAR).first()
    assert track is not None
    in_track = _entry("in-track", on=date(1845, 1, 1))
    TrackEntry.objects.create(track=track, entry=in_track, position=1)
    person = _entry("person", Entry.Type.PERSON)
    EntryRelation.objects.create(from_entry=person, to_entry=in_track)
    other = _entry("other", on=date(1800, 1, 1))
    _read(user, in_track, person, other)
    phase = Phase.objects.create(name="T", start_date=date(1840, 1, 1), end_date=date(1850, 1, 1))

    assert _prompts(client.get(f"/api/practice?track={track.pk}")) == {"in-track", "person"}
    assert _prompts(client.get(f"/api/practice?phase={phase.pk}")) == {"in-track", "person"}
    assert _prompts(client.get("/api/practice")) == {"in-track", "person", "other"}


def test_count(client: Client, user: User) -> None:
    _read(user, _entry("a", questions=15), _entry("b", questions=15))
    assert len(client.get("/api/practice").json()["questions"]) == 10
    assert len(client.get("/api/practice?count=20").json()["questions"]) == 20
    assert client.get("/api/practice?count=21").status_code == 422
    assert client.get("/api/practice?count=0").status_code == 422


def test_count_limited_by_pool(client: Client, user: User) -> None:
    _read(user, _entry("a", questions=3))
    assert len(client.get("/api/practice").json()["questions"]) == 3


def _answer(client: Client, question: Question, answer: Any) -> Any:
    return client.post(
        "/api/practice/answer",
        {"question_id": question.pk, "answer": answer},
        content_type="application/json",
    )


def test_correct_answer_gives_xp_every_time(client: Client, user: User) -> None:
    entry = _entry("a")
    _read(user, entry)
    question = entry.questions.all()[0]
    result = _answer(client, question, True).json()
    assert result == {
        "correct": True,
        "correct_answer": True,
        "explanation": "Because a 0",
        "xp_awarded": 2,
    }
    assert _answer(client, question, True).json()["xp_awarded"] == 2
    assert XpEvent.objects.filter(kind="practice").count() == 2


def test_wrong_answer_explains_without_side_effects(client: Client, user: User) -> None:
    entry = _entry("a")
    _read(user, entry)
    result = _answer(client, entry.questions.all()[0], False).json()
    assert result["correct"] is False
    assert (result["correct_answer"], result["xp_awarded"]) == (True, 0)
    assert result["explanation"] == "Because a 0"
    assert not QuestionState.objects.exists()
    assert not QuizAttempt.objects.exists()
    assert not XpEvent.objects.filter(kind="practice").exists()


def test_only_read_entries_can_be_answered(client: Client, user: User) -> None:
    unread = _entry("unread")
    assert _answer(client, unread.questions.all()[0], True).status_code == 403
    other = Client()
    other.force_login(User.objects.create_user("other", password="pw"))
    _read(user, unread)
    assert _answer(other, unread.questions.all()[0], True).status_code == 403
    assert _answer(client, unread.questions.all()[0], True).status_code == 200


def test_unknown_or_malformed(client: Client, user: User) -> None:
    entry = _entry("a")
    _read(user, entry)
    assert (
        client.post(
            "/api/practice/answer",
            {"question_id": 999999, "answer": True},
            content_type="application/json",
        ).status_code
        == 404
    )
    assert _answer(client, entry.questions.all()[0], "yes").status_code == 400
