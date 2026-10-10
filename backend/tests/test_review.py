from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.content.models import Entry, Track, TrackEntry
from apps.gamification.models import XpEvent
from apps.progress.models import QuestionState
from apps.quizzes.models import Question

NOW = datetime(2026, 3, 10, 9, tzinfo=UTC)
TODAY = NOW.date()


def _event(slug: str, position: int, published: bool = True) -> Entry:
    entry = Entry.objects.create(
        type=Entry.Type.EVENT,
        slug=slug,
        title=f"Title {slug}",
        summary="x",
        event_date=date(1800, 1, 1),
        importance=Entry.Importance.MAJOR,
        status=Entry.Status.PUBLISHED if published else Entry.Status.DRAFT,
    )
    TrackEntry.objects.create(
        track=Track.objects.get(kind=Track.Kind.OPENING), entry=entry, position=position
    )
    return entry


def _question(entry: Entry, due: date, box: int = 0, prompt: str = "Вярно ли е?") -> Question:
    question = Question.objects.create(
        entry=entry,
        type="true_false",
        prompt=prompt,
        payload={"answer": True},
        explanation=f"Because {prompt}",
    )
    QuestionState.objects.create(
        user=User.objects.get(),
        question=question,
        box=box,
        due_date=due,
        miss_count=1,
        last_answered_at=NOW,
    )
    return question


@pytest.fixture
def client(db: None, monkeypatch: pytest.MonkeyPatch) -> Client:
    monkeypatch.setattr("apps.core.clock.now", lambda user=None: NOW)
    client = Client()
    client.force_login(User.objects.create_user("learner", password="pw"))
    return client


@pytest.fixture
def first(client: Client) -> Entry:
    return _event("first", 1)


def _answer(client: Client, question: Question, answer: Any) -> Any:
    return client.post(
        "/api/review/answer",
        {"question_id": question.pk, "answer": answer},
        content_type="application/json",
    )


def _state(question: Question) -> QuestionState:
    return QuestionState.objects.get(question=question)


def test_queue_has_due_questions_most_overdue_first(client: Client, first: Entry) -> None:
    today = _question(first, TODAY, prompt="today")
    overdue = _question(first, TODAY - timedelta(days=3), prompt="overdue")
    _question(first, TODAY + timedelta(days=1), prompt="later")
    response = client.get("/api/review")
    assert [q["id"] for q in response.json()["questions"]] == [overdue.pk, today.pk]
    assert "Because" not in response.content.decode()
    assert '"answer"' not in response.content.decode()


def test_queue_skips_locked_and_draft_entries(client: Client, first: Entry) -> None:
    _question(_event("second", 2), TODAY)  # locked: first is not read
    _question(_event("draft", 3, published=False), TODAY)
    assert client.get("/api/review").json() == {"questions": []}
    assert client.get("/api/dashboard").json()["reviews_due"] == 0


def test_correct_answer_moves_up_and_awards_xp(client: Client, first: Entry) -> None:
    question = _question(first, TODAY)
    result = _answer(client, question, True).json()
    assert result == {
        "correct": True,
        "explanation": "Because Вярно ли е?",
        "xp_awarded": 2,
        "next_due_date": "2026-03-13",
        "entry": None,
    }
    assert (_state(question).box, _state(question).miss_count) == (1, 1)
    assert XpEvent.objects.filter(kind="review").count() == 1


@pytest.mark.parametrize(
    ("box", "new_box", "days"), [(0, 1, 3), (1, 2, 7), (2, 3, 14), (3, 4, 30), (4, 4, 30)]
)
def test_intervals(client: Client, first: Entry, box: int, new_box: int, days: int) -> None:
    question = _question(first, TODAY, box=box)
    _answer(client, question, True)
    state = _state(question)
    assert (state.box, state.due_date) == (new_box, TODAY + timedelta(days=days))


def test_wrong_answer_resets_and_links_entry(client: Client, first: Entry) -> None:
    question = _question(first, TODAY - timedelta(days=1), box=3)
    result = _answer(client, question, False).json()
    assert result["correct"] is False
    assert result["explanation"] == "Because Вярно ли е?"
    assert result["xp_awarded"] == 0
    assert result["entry"] == {"slug": "first", "title": "Title first"}
    state = _state(question)
    assert (state.box, state.due_date, state.miss_count) == (0, TODAY + timedelta(days=1), 2)
    assert not XpEvent.objects.filter(kind="review").exists()


def test_only_due_questions_can_be_answered(client: Client, first: Entry) -> None:
    later = _question(first, TODAY + timedelta(days=1))
    assert _answer(client, later, True).status_code == 409
    due = _question(first, TODAY, prompt="due")
    assert _answer(client, due, True).status_code == 200
    assert _answer(client, due, True).status_code == 409  # no farming the same question
    locked = _question(_event("second", 2), TODAY, prompt="locked")
    assert _answer(client, locked, True).status_code == 409
    no_state = Question.objects.create(
        entry=first, type="true_false", prompt="?", payload={"answer": True}, explanation="x"
    )
    assert _answer(client, no_state, True).status_code == 409


def test_malformed_answer_leaves_state(client: Client, first: Entry) -> None:
    question = _question(first, TODAY, box=2)
    assert _answer(client, question, "yes").status_code == 400
    assert (_state(question).box, _state(question).due_date) == (2, TODAY)


def test_answers_belong_to_the_user(client: Client, first: Entry) -> None:
    question = _question(first, TODAY)
    other = Client()
    other.force_login(User.objects.create_user("other", password="pw"))
    assert _answer(other, question, True).status_code == 409
