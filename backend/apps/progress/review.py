"""Spaced repetition (scope 5, architecture 6.3)."""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import QuerySet

from apps.core import clock
from apps.core.app_settings import get_setting
from apps.gamification import xp
from apps.gamification.models import XpEvent
from apps.quizzes.grading import answer_error, is_correct
from apps.quizzes.models import Question

from .models import QuestionState
from .unlock import unlocked_entry_ids

INTERVAL_DAYS = [1, 3, 7, 14, 30]


class NotDue(Exception):
    """Only questions in today's queue can be answered."""


class InvalidAnswer(Exception):
    pass


def record_miss(user: User, question_id: int) -> QuestionState:
    """A wrong answer creates the state or resets it to the first interval."""
    now = clock.now(user)
    state, _ = QuestionState.objects.get_or_create(
        user=user,
        question_id=question_id,
        defaults={"due_date": now.date(), "last_answered_at": now},
    )
    state.box = 0
    state.due_date = now.date() + timedelta(days=INTERVAL_DAYS[0])
    state.miss_count += 1
    state.last_answered_at = now
    state.save()
    return state


def missed_question_ids(user: User, question_ids: list[int]) -> set[int]:
    rows = QuestionState.objects.filter(
        user=user, question_id__in=question_ids, miss_count__gt=0
    ).values_list("question_id", flat=True)
    return set(rows)


def _due(user: User, today: date) -> QuerySet[QuestionState]:
    """Due states whose entry the user can still open (drafts and locked entries wait)."""
    return QuestionState.objects.filter(
        user=user,
        due_date__lte=today,
        question__entry_id__in=unlocked_entry_ids(user),
    )


def due_count(user: User, today: date) -> int:
    return _due(user, today).count()


def review_queue(user: User) -> list[Question]:
    """Today's review questions, the most overdue first."""
    states = _due(user, clock.now(user).date()).select_related("question")
    return [s.question for s in states.order_by("due_date", "id")]


@dataclass(frozen=True)
class ReviewResult:
    question: Question
    correct: bool
    xp_awarded: int
    next_due: date


def answer_review(user: User, question_id: int, answer: Any) -> ReviewResult:
    """Grade one review answer. Correct moves the question up one interval (staying at the
    last one); wrong resets it to the first."""
    now = clock.now(user)
    today = now.date()
    with transaction.atomic():
        state = (
            _due(user, today)
            .select_for_update(of=("self",))
            .select_related("question")
            .filter(question_id=question_id)
            .first()
        )
        if state is None:
            raise NotDue
        question = state.question
        error = answer_error(question.type, answer)
        if error:
            raise InvalidAnswer(error)

        if not is_correct(question.type, question.payload, answer):
            state = record_miss(user, question_id)
            return ReviewResult(question, False, 0, state.due_date)

        state.box = min(state.box + 1, len(INTERVAL_DAYS) - 1)
        state.due_date = today + timedelta(days=INTERVAL_DAYS[state.box])
        state.last_answered_at = now
        state.save(update_fields=["box", "due_date", "last_answered_at"])
        event = xp.award(
            user, XpEvent.Kind.REVIEW, get_setting("xp_review_correct"), f"question:{question_id}"
        )
    return ReviewResult(question, True, event.amount if event else 0, state.due_date)
