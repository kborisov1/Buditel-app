import random
from collections import Counter
from datetime import UTC, date, datetime
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.content.models import Entry, Track, TrackEntry
from apps.core.app_settings import get_setting
from apps.core.models import AppSetting
from apps.gamification.models import XpEvent
from apps.progress.models import EntryProgress, QuestionState
from apps.quizzes.grading import answer_error, is_correct, normalize_blank
from apps.quizzes.models import Question, QuizAttempt
from apps.quizzes.quiz import draw, passes, shown_question

NOW = datetime(2026, 3, 10, 9, tzinfo=UTC)

PAYLOADS: list[tuple[str, str, dict[str, Any], Any, Any]] = [
    # type, prompt, payload, a correct answer, a wrong answer
    ("multiple_choice", "Кой?", {"options": ["А", "Б", "В"], "correct": 1}, 1, 0),
    ("true_false", "Вярно ли е?", {"answer": True}, True, False),
    (
        "date_ordering",
        "Подредете",
        {"items": ["1762", "1835", "1876"]},
        ["1762", "1835", "1876"],
        ["1835", "1762", "1876"],
    ),
    (
        "fill_blank",
        "Паисий пише ___.",
        {"answers": ["История славянобългарска"]},
        "история  славянобългарска!",
        "Друго",
    ),
]


# Grading


@pytest.mark.parametrize(("qtype", "prompt", "payload", "right", "wrong"), PAYLOADS)
def test_grading(qtype: str, prompt: str, payload: dict[str, Any], right: Any, wrong: Any) -> None:
    assert is_correct(qtype, payload, right)
    assert not is_correct(qtype, payload, wrong)
    assert answer_error(qtype, right) is None


def test_fill_blank_normalization() -> None:
    assert normalize_blank("  Св. Иван   Рилски, ") == "св иван рилски"


@pytest.mark.parametrize(
    ("qtype", "answer"),
    [
        ("multiple_choice", True),
        ("multiple_choice", "1"),
        ("true_false", 1),
        ("date_ordering", "1762"),
        ("date_ordering", [1762]),
        ("fill_blank", 3),
    ],
)
def test_wrong_answer_shape(qtype: str, answer: Any) -> None:
    assert answer_error(qtype, answer) is not None


def test_true_false_does_not_accept_one_as_true() -> None:
    assert not is_correct("true_false", {"answer": True}, 1)


@pytest.mark.parametrize(
    ("score", "pct", "expected"), [(4, 80, True), (3, 80, False), (5, 100, True), (3, 60, True)]
)
def test_pass_mark(score: int, pct: int, expected: bool) -> None:
    assert passes(score, 5, pct) is expected


# Draw


def test_draw_picks_five_distinct() -> None:
    chosen = draw(list(range(10)), set(), 3, random.Random(1))
    assert len(chosen) == len(set(chosen)) == 5


def test_draw_with_small_pool_returns_all() -> None:
    assert sorted(draw([1, 2, 3], set(), 3, random.Random(1))) == [1, 2, 3]


def test_draw_favors_missed_questions() -> None:
    rng, pool, counts = random.Random(7), list(range(10)), Counter[int]()
    for _ in range(3000):
        counts.update(draw(pool, {0}, 3, rng))
    others = sum(counts[q] for q in pool[1:]) / 9
    assert counts[0] > 1.5 * others  # missed one is drawn clearly more often
    assert counts[0] / 3000 > 0.75


def test_draw_weight_one_is_uniform() -> None:
    rng, counts = random.Random(7), Counter[int]()
    for _ in range(3000):
        counts.update(draw(list(range(10)), {0}, 1, rng))
    assert 0.4 < counts[0] / 3000 < 0.6


def test_shown_question_hides_answers() -> None:
    for qtype, prompt, payload, _, _ in PAYLOADS:
        question = Question(pk=1, type=qtype, prompt=prompt, payload=payload)
        shown = shown_question(question, random.Random(0))
        assert {"correct", "answer", "answers", "explanation"}.isdisjoint(shown)
        if qtype == "date_ordering":
            assert shown["items"] != payload["items"]
            assert sorted(shown["items"]) == sorted(payload["items"])


# Flow through the API


def test_quiz_settings_seeded(db: None) -> None:
    assert get_setting("quiz_pass_percentage") == 80
    assert get_setting("quiz_missed_weight") == 3
    assert get_setting("xp_quiz_first_pass") == 50
    assert get_setting("xp_quiz_retake") == 5


def _event(slug: str) -> Entry:
    entry = Entry.objects.create(
        type=Entry.Type.EVENT,
        slug=slug,
        title=slug,
        summary="x",
        event_date=date(1800, 1, 1),
        importance=Entry.Importance.MAJOR,
        status=Entry.Status.PUBLISHED,
    )
    for i in range(6):
        qtype, prompt, payload, _, _ = PAYLOADS[i % len(PAYLOADS)]
        Question.objects.create(
            entry=entry,
            type=qtype,
            prompt=f"{prompt} {i}",
            payload=payload,
            explanation=f"Explanation {slug} {i}",
        )
    return entry


@pytest.fixture
def user(db: None) -> User:
    return User.objects.create_user("learner", password="pw")


@pytest.fixture
def client(user: User, monkeypatch: pytest.MonkeyPatch) -> Client:
    monkeypatch.setattr("apps.core.clock.now", lambda user=None: NOW)
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def entries(db: None) -> tuple[Entry, Entry]:
    first, second = _event("first"), _event("second")
    track = Track.objects.get(kind=Track.Kind.OPENING)
    TrackEntry.objects.create(track=track, entry=first, position=1)
    TrackEntry.objects.create(track=track, entry=second, position=2)
    return first, second


def _start(client: Client, slug: str = "first") -> dict[str, Any]:
    client.post(f"/api/entries/{slug}/finished-reading")
    response = client.post(f"/api/entries/{slug}/quiz")
    assert response.status_code == 200
    return response.json()  # type: ignore[no-any-return]


def _answers(quiz: dict[str, Any], wrong: int = 0) -> list[dict[str, Any]]:
    out = []
    for n, shown in enumerate(quiz["questions"]):
        question = Question.objects.get(pk=shown["id"])
        right, bad = next((r, w) for t, _, _, r, w in PAYLOADS if t == question.type)
        out.append({"question_id": question.pk, "answer": bad if n < wrong else right})
    return out


def _submit(client: Client, quiz: dict[str, Any], wrong: int = 0) -> Any:
    return client.post(
        f"/api/quiz-attempts/{quiz['attempt_id']}/submit",
        {"answers": _answers(quiz, wrong)},
        content_type="application/json",
    )


def test_start_needs_finished_reading(client: Client, entries: tuple[Entry, Entry]) -> None:
    assert client.post("/api/entries/first/quiz").status_code == 409


def test_start_locked_or_missing(client: Client, entries: tuple[Entry, Entry]) -> None:
    assert client.post("/api/entries/second/quiz").status_code == 403
    assert client.post("/api/entries/nope/quiz").status_code == 404


def test_start_sends_five_questions_without_answers(
    client: Client, entries: tuple[Entry, Entry]
) -> None:
    client.post("/api/entries/first/finished-reading")
    response = client.post("/api/entries/first/quiz")
    quiz = response.json()
    assert len(quiz["questions"]) == 5
    content = response.content.decode()
    for leak in ['"correct"', '"answers"', '"answer"', "Explanation", "История"]:
        assert leak not in content


def test_pass_marks_read_awards_xp_and_unlocks(
    client: Client, user: User, entries: tuple[Entry, Entry]
) -> None:
    result = _submit(client, _start(client), wrong=1).json()
    assert (result["passed"], result["score"], result["total"]) == (True, 4, 5)
    assert result["xp_awarded"] == 50
    assert len(result["results"]) == 5
    assert all(r["explanation"].startswith("Explanation first") for r in result["results"])
    assert [r["correct"] for r in result["results"]].count(False) == 1

    progress = EntryProgress.objects.get(user=user, entry=entries[0])
    assert (progress.state, progress.passed_at) == ("read", NOW)
    (event,) = XpEvent.objects.filter(user=user)
    assert (event.kind, event.amount, event.local_date) == ("quiz_first_pass", 50, NOW.date())
    user.profile.refresh_from_db()  # type: ignore[attr-defined]
    assert user.profile.completed_entries_count == 1  # type: ignore[attr-defined]
    assert client.get("/api/entries/second").json()["locked"] is False


def test_fail_returns_score_only(client: Client, user: User, entries: tuple[Entry, Entry]) -> None:
    response = _submit(client, _start(client), wrong=2)
    assert response.json() == {"passed": False, "score": 3, "total": 5}
    assert "Explanation" not in response.content.decode()
    assert EntryProgress.objects.get(user=user).state == "in_progress"
    assert not XpEvent.objects.exists()
    assert client.get("/api/entries/second").json()["locked"] is True


def test_misses_create_review_state(
    client: Client, user: User, entries: tuple[Entry, Entry]
) -> None:
    quiz = _start(client)
    _submit(client, quiz, wrong=2)
    states = QuestionState.objects.filter(user=user)
    assert {s.question_id for s in states} == {q["id"] for q in quiz["questions"][:2]}
    assert all((s.box, s.due_date, s.miss_count) == (0, date(2026, 3, 11), 1) for s in states)


def test_miss_resets_existing_state(
    client: Client, user: User, entries: tuple[Entry, Entry]
) -> None:
    quiz = _start(client)
    missed = quiz["questions"][0]["id"]
    QuestionState.objects.create(
        user=user,
        question_id=missed,
        box=3,
        due_date=date(2026, 4, 1),
        miss_count=2,
        last_answered_at=NOW,
    )
    _submit(client, quiz, wrong=1)
    state = QuestionState.objects.get(user=user, question_id=missed)
    assert (state.box, state.due_date, state.miss_count) == (0, date(2026, 3, 11), 3)


def test_fail_then_pass_is_first_pass(
    client: Client, user: User, entries: tuple[Entry, Entry]
) -> None:
    _submit(client, _start(client), wrong=3)
    assert _submit(client, _start(client)).json()["xp_awarded"] == 50


def test_retake_gives_reduced_xp(client: Client, user: User, entries: tuple[Entry, Entry]) -> None:
    _submit(client, _start(client))
    assert _submit(client, _start(client)).json()["xp_awarded"] == 5
    assert XpEvent.objects.filter(kind="quiz_retake").count() == 1
    assert EntryProgress.objects.get(user=user).passed_at == NOW
    user.profile.refresh_from_db()  # type: ignore[attr-defined]
    assert user.profile.completed_entries_count == 1  # type: ignore[attr-defined]


def test_settings_drive_pass_mark_and_xp(client: Client, entries: tuple[Entry, Entry]) -> None:
    AppSetting.objects.filter(key="quiz_pass_percentage").update(value=60)
    AppSetting.objects.filter(key="xp_quiz_first_pass").update(value=40)
    result = _submit(client, _start(client), wrong=2).json()
    assert (result["passed"], result["xp_awarded"]) == (True, 40)


def test_submit_twice_conflicts(client: Client, entries: tuple[Entry, Entry]) -> None:
    quiz = _start(client)
    _submit(client, quiz)
    assert _submit(client, quiz).status_code == 409


def test_cannot_submit_another_users_attempt(client: Client, entries: tuple[Entry, Entry]) -> None:
    quiz = _start(client)
    other = Client()
    other.force_login(User.objects.create_user("other", password="pw"))
    assert _submit(other, quiz).status_code == 404


def test_incomplete_or_malformed_answers_rejected(
    client: Client, entries: tuple[Entry, Entry]
) -> None:
    quiz = _start(client)
    url = f"/api/quiz-attempts/{quiz['attempt_id']}/submit"
    answers = _answers(quiz)

    def post(body: list[dict[str, Any]]) -> int:
        return client.post(url, {"answers": body}, content_type="application/json").status_code

    assert post(answers[:4]) == 400
    assert post([*answers, answers[0]]) == 400
    mc = next(a for a in answers if isinstance(a["answer"], int) and a["answer"] is not True)
    assert post([a if a is not mc else {**a, "answer": "1"} for a in answers]) == 400
    assert QuizAttempt.objects.get().submitted_at is None
    assert post(answers) == 200


def test_submit_requires_csrf(user: User, entries: tuple[Entry, Entry]) -> None:
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    response = client.post(
        "/api/quiz-attempts/1/submit", {"answers": []}, content_type="application/json"
    )
    assert response.status_code == 403
