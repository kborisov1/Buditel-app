"""Practice (scope 7.5, architecture 6.7): relaxed questions from entries the user has read.

No quiz attempt is created and misses do not touch review.
"""

import random
from dataclasses import dataclass
from typing import Any

from django.contrib.auth.models import User

from apps.content.library import filter_entries, published_entries
from apps.core.app_settings import get_setting
from apps.gamification import xp
from apps.gamification.models import XpEvent
from apps.progress.unlock import read_entry_ids, unlocked_entry_ids

from .grading import answer_error, is_correct
from .models import Question

DEFAULT_COUNT = 10
MAX_COUNT = 20


class NotPracticable(Exception):
    """The question's entry is not read (or no longer open) for this user."""


class InvalidAnswer(Exception):
    pass


def _practice_entry_ids(user: User) -> set[int]:
    return read_entry_ids(user) & unlocked_entry_ids(user)


def practice_questions(
    user: User,
    *,
    track_id: int | None = None,
    phase_id: int | None = None,
    count: int = DEFAULT_COUNT,
    rng: random.Random | None = None,
) -> list[Question]:
    """A random set from read entries, filtered by topic (track) and period (phase)."""
    entries = filter_entries(
        published_entries().filter(pk__in=_practice_entry_ids(user)),
        track_id=track_id,
        phase_id=phase_id,
    )
    pool = list(Question.objects.filter(entry__in=entries).order_by("id"))
    return (rng or random.Random()).sample(pool, min(count, len(pool)))


@dataclass(frozen=True)
class PracticeResult:
    question: Question
    correct: bool
    xp_awarded: int


def answer_practice(user: User, question_id: int, answer: Any) -> PracticeResult:
    question = Question.objects.select_related("entry").get(pk=question_id)
    if question.entry_id not in _practice_entry_ids(user):
        raise NotPracticable
    error = answer_error(question.type, answer)
    if error:
        raise InvalidAnswer(error)
    if not is_correct(question.type, question.payload, answer):
        return PracticeResult(question, False, 0)
    event = xp.award(
        user, XpEvent.Kind.PRACTICE, get_setting("xp_review_correct"), f"question:{question_id}"
    )
    return PracticeResult(question, True, event.amount if event else 0)
