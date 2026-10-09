"""Post-reading quiz: draw, grade, and what a pass unlocks (scope 4, architecture 6.2)."""

import random
from dataclasses import dataclass
from typing import Any

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F

from apps.accounts.models import Profile
from apps.content.models import Entry
from apps.core import clock
from apps.core.app_settings import get_setting
from apps.gamification import xp
from apps.gamification.models import XpEvent
from apps.progress.models import EntryProgress
from apps.progress.reading import EntryLocked
from apps.progress.review import missed_question_ids, record_miss
from apps.progress.unlock import is_unlocked

from .grading import answer_error, is_correct
from .models import Question, QuizAttempt, QuizAttemptQuestion

QUIZ_SIZE = 5


class QuizError(Exception):
    pass


class ReadingNotFinished(QuizError):
    """The quiz opens only after "Finished reading" (scope 4)."""


class AlreadySubmitted(QuizError):
    pass


class InvalidAnswers(QuizError):
    pass


def draw(question_ids: list[int], missed: set[int], weight: int, rng: random.Random) -> list[int]:
    """Weighted draw without replacement; missed questions count `weight` times.

    Uses Efraimidis-Spirakis keys: each question gets random() ** (1 / weight).
    """
    keyed = sorted(
        question_ids,
        key=lambda q: rng.random() ** (1 / (weight if q in missed else 1)),
        reverse=True,
    )
    return keyed[:QUIZ_SIZE]


def start_quiz(user: User, entry: Entry, rng: random.Random | None = None) -> QuizAttempt:
    if not is_unlocked(user, entry.pk):
        raise EntryLocked
    if not EntryProgress.objects.filter(user=user, entry=entry).exists():
        raise ReadingNotFinished
    pool = list(entry.questions.values_list("id", flat=True))
    chosen = draw(
        pool,
        missed_question_ids(user, pool),
        get_setting("quiz_missed_weight"),
        rng or random.Random(),
    )
    with transaction.atomic():
        attempt = QuizAttempt.objects.create(user=user, entry=entry, started_at=clock.now(user))
        QuizAttemptQuestion.objects.bulk_create(
            QuizAttemptQuestion(attempt=attempt, question_id=q, position=i)
            for i, q in enumerate(chosen, start=1)
        )
    return attempt


@dataclass(frozen=True)
class QuizResult:
    attempt: QuizAttempt
    items: list[QuizAttemptQuestion]

    @property
    def total(self) -> int:
        return len(self.items)


def passes(score: int, total: int, percentage: int) -> bool:
    return score * 100 >= percentage * total


def submit_quiz(user: User, attempt_id: int, answers: dict[int, Any]) -> QuizResult:
    """Grade all answers at once. A pass marks the entry read and awards XP."""
    with transaction.atomic():
        attempt = QuizAttempt.objects.select_for_update().get(pk=attempt_id, user=user)
        if attempt.submitted_at is not None:
            raise AlreadySubmitted
        items = list(attempt.items.select_related("question"))
        _check_answers(items, answers)

        for item in items:
            item.answer = answers[item.question_id]
            item.correct = is_correct(item.question.type, item.question.payload, item.answer)
            if not item.correct:
                record_miss(user, item.question_id)
        QuizAttemptQuestion.objects.bulk_update(items, ["answer", "correct"])

        attempt.score = sum(1 for i in items if i.correct)
        attempt.passed = passes(attempt.score, len(items), get_setting("quiz_pass_percentage"))
        attempt.submitted_at = clock.now(user)
        if attempt.passed:
            attempt.xp_awarded = _record_pass(user, attempt)
        attempt.save()
    return QuizResult(attempt, items)


def _check_answers(items: list[QuizAttemptQuestion], answers: dict[int, Any]) -> None:
    if set(answers) != {i.question_id for i in items}:
        raise InvalidAnswers("Answer every question in the quiz, and only those.")
    for item in items:
        error = answer_error(item.question.type, answers[item.question_id])
        if error:
            raise InvalidAnswers(f"Question {item.question_id}: {error}")


def _record_pass(user: User, attempt: QuizAttempt) -> int:
    """Mark the entry read. The first pass gives full XP and counts toward the older-event
    check (architecture 6.4); later passes are retakes."""
    progress = EntryProgress.objects.select_for_update().get(user=user, entry=attempt.entry)
    first_pass = progress.state != EntryProgress.State.READ
    if first_pass:
        progress.state = EntryProgress.State.READ
        progress.passed_at = attempt.submitted_at
        progress.save(update_fields=["state", "passed_at"])
        Profile.objects.filter(user=user).update(
            completed_entries_count=F("completed_entries_count") + 1
        )
        kind, amount = XpEvent.Kind.QUIZ_FIRST_PASS, get_setting("xp_quiz_first_pass")
    else:
        kind, amount = XpEvent.Kind.QUIZ_RETAKE, get_setting("xp_quiz_retake")
    if amount:
        xp.award(user, kind, amount, reference=f"quiz_attempt:{attempt.pk}")
    return int(amount)


def shown_question(question: Question, rng: random.Random | None = None) -> dict[str, Any]:
    """What the learner sees before answering. Never includes the correct answer."""
    shown: dict[str, Any] = {"id": question.pk, "type": question.type, "prompt": question.prompt}
    if question.type == Question.Type.MULTIPLE_CHOICE:
        shown["options"] = question.payload["options"]
    elif question.type == Question.Type.DATE_ORDERING:
        items, rng = list(question.payload["items"]), rng or random.Random()
        while items == question.payload["items"]:  # never show the answer as the start order
            rng.shuffle(items)
        shown["items"] = items
    return shown
