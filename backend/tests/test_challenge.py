import random
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.content.models import Entry
from apps.gamification.models import XpEvent
from apps.progress.models import EntryProgress, QuestionState
from apps.quizzes.challenge import CHALLENGE_SIZE, pick_questions
from apps.quizzes.models import (
    DailyChallenge,
    Question,
    QuizAttempt,
    QuizAttemptQuestion,
)
from apps.quizzes.weak_topics import entry_weakness

NOW = datetime(2026, 3, 10, 9, tzinfo=UTC)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> list[datetime]:
    current = [NOW]
    monkeypatch.setattr("apps.core.clock.now", lambda user=None: current[0])
    return current


@pytest.fixture
def user(db: None, clock: list[datetime]) -> User:
    return User.objects.create_user("learner", password="pw")


@pytest.fixture
def client(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


def _entry(slug: str, questions: int = 6, read_by: User | None = None) -> Entry:
    entry = Entry.objects.create(
        type=Entry.Type.EVENT,
        slug=slug,
        title=slug,
        summary="x",
        event_date=date(1800, 1, 1),
        importance=Entry.Importance.MAJOR,
        status=Entry.Status.PUBLISHED,
    )
    for i in range(questions):
        Question.objects.create(
            entry=entry,
            type="true_false",
            prompt=f"{slug} {i}",
            payload={"answer": True},
            explanation=f"Because {slug} {i}",
        )
    if read_by:
        EntryProgress.objects.create(
            user=read_by, entry=entry, state="read", finished_reading_at=NOW, passed_at=NOW
        )
    return entry


def _answered(user: User, entry: Entry, results: list[bool], days_ago: float = 0) -> None:
    """Record graded quiz answers for the entry's first questions."""
    at = NOW - timedelta(days=days_ago)
    attempt = QuizAttempt.objects.create(
        user=user, entry=entry, started_at=at, submitted_at=at, score=0, passed=False
    )
    for position, (question, correct) in enumerate(
        zip(entry.questions.all(), results, strict=False), start=1
    ):
        QuizAttemptQuestion.objects.create(
            attempt=attempt, question=question, position=position, correct=correct
        )


def _entries_of(question_ids: list[int]) -> list[str]:
    slugs = dict(Question.objects.filter(pk__in=question_ids).values_list("id", "entry__slug"))
    return [slugs[q] for q in question_ids]


# Weakness (scope 6.6)


def test_weakness_is_miss_rate(user: User) -> None:
    entry, perfect = _entry("a"), _entry("b")
    _answered(user, entry, [False, True, True, False])
    _answered(user, perfect, [True, True])
    assert entry_weakness(user) == {entry.pk: 0.5, perfect.pk: 0.0}


def test_recent_misses_weigh_more(user: User) -> None:
    old_miss, new_miss = _entry("old"), _entry("new")
    _answered(user, old_miss, [False], days_ago=14)
    _answered(user, old_miss, [True])
    _answered(user, new_miss, [True], days_ago=14)
    _answered(user, new_miss, [False])
    weakness = entry_weakness(user)
    assert weakness[old_miss.pk] == pytest.approx(1 / 3)
    assert weakness[new_miss.pk] == pytest.approx(2 / 3)


def test_ungraded_answers_ignored(user: User) -> None:
    entry = _entry("a")
    attempt = QuizAttempt.objects.create(user=user, entry=entry, started_at=NOW)
    QuizAttemptQuestion.objects.create(
        attempt=attempt, question=entry.questions.all()[0], position=1
    )
    assert entry_weakness(user) == {}


# Picking (scope 6.5)


def test_pick_weakest_entries_in_turn(user: User) -> None:
    weakest, weak, fine = (_entry(s, read_by=user) for s in ["weakest", "weak", "fine"])
    _answered(user, weakest, [False, False])
    _answered(user, weak, [False, True])
    _answered(user, fine, [True, True])
    chosen = pick_questions(user, random.Random(0))
    assert len(chosen) == CHALLENGE_SIZE
    entries = _entries_of(chosen)
    assert entries[:4] == ["weakest", "weak", "weakest", "weak"]
    assert "fine" not in entries


def test_pick_missed_questions_first(user: User) -> None:
    entry = _entry("a", read_by=user)
    _answered(user, entry, [True, False])
    missed = entry.questions.all()[1]
    QuestionState.objects.create(
        user=user, question=missed, due_date=NOW.date(), miss_count=1, last_answered_at=NOW
    )
    for seed in range(5):
        assert pick_questions(user, random.Random(seed))[0] == missed.pk


def test_pick_fills_from_other_read_entries(user: User) -> None:
    weak = _entry("weak", questions=2, read_by=user)
    _answered(user, weak, [False])
    for slug in ["b", "c"]:
        _entry(slug, read_by=user)
    _entry("unread")
    entries = _entries_of(pick_questions(user, random.Random(0)))
    assert len(entries) == CHALLENGE_SIZE
    assert entries[:2] == ["weak", "weak"]
    assert set(entries[2:]) <= {"b", "c"}


def test_pick_small_pool_and_empty(user: User) -> None:
    assert pick_questions(user, random.Random(0)) == []
    _entry("a", questions=6, read_by=user)
    assert len(pick_questions(user, random.Random(0))) == 6


# API flow


def test_no_challenge_without_read_entries(client: Client) -> None:
    data = client.get("/api/daily-challenge").json()
    assert data == {"id": None, "date": "2026-03-10", "completed": False, "questions": []}
    assert not DailyChallenge.objects.exists()


def test_challenge_fixed_for_the_day(client: Client, user: User, clock: list[datetime]) -> None:
    _entry("a", questions=12, read_by=user)
    first = client.get("/api/daily-challenge")
    data = first.json()
    assert len(data["questions"]) == 10
    assert "Because" not in first.content.decode()
    again = client.get("/api/daily-challenge").json()
    assert again["id"] == data["id"]
    assert {q["question"]["id"] for q in again["questions"]} == {
        q["question"]["id"] for q in data["questions"]
    }
    clock[0] = NOW + timedelta(days=1)
    assert client.get("/api/daily-challenge").json()["id"] != data["id"]


def _answer(client: Client, question_id: int, answer: Any) -> Any:
    return client.post(
        "/api/daily-challenge/answer",
        {"question_id": question_id, "answer": answer},
        content_type="application/json",
    )


def test_answer_flow_and_completion(client: Client, user: User) -> None:
    _entry("a", questions=3, read_by=user)
    ids = [q["question"]["id"] for q in client.get("/api/daily-challenge").json()["questions"]]

    right = _answer(client, ids[0], True).json()
    assert right == {
        "correct": True,
        "correct_answer": True,
        "explanation": right["explanation"],
        "xp_awarded": 2,
        "completed": False,
        "bonus_xp": 0,
    }
    assert right["explanation"].startswith("Because a")
    wrong = _answer(client, ids[1], False).json()
    assert (wrong["correct"], wrong["xp_awarded"]) == (False, 0)
    assert QuestionState.objects.filter(user=user, question_id=ids[1]).exists()

    last = _answer(client, ids[2], True).json()
    assert (last["completed"], last["bonus_xp"]) == (True, 10)
    data = client.get("/api/daily-challenge").json()
    assert data["completed"] is True
    assert [(q["answered"], q["correct"]) for q in data["questions"]] == [
        (True, True),
        (True, False),
        (True, True),
    ]
    assert (
        sum(XpEvent.objects.filter(kind="daily_challenge").values_list("amount", flat=True)) == 14
    )


def test_answer_rules(client: Client, user: User, clock: list[datetime]) -> None:
    _entry("a", questions=12, read_by=user)
    ids = [q["question"]["id"] for q in client.get("/api/daily-challenge").json()["questions"]]
    outside = Question.objects.exclude(pk__in=ids).first()
    assert outside is not None
    assert _answer(client, outside.pk, True).status_code == 409
    assert _answer(client, ids[0], "yes").status_code == 400
    assert _answer(client, ids[0], True).status_code == 200
    assert _answer(client, ids[0], True).status_code == 409  # already answered
    clock[0] = NOW + timedelta(days=1)
    assert _answer(client, ids[1], True).status_code == 409  # yesterday's challenge
