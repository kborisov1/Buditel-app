"""Spaced repetition state (scope 5, architecture 6.3)."""

from datetime import timedelta

from django.contrib.auth.models import User

from apps.core import clock

from .models import QuestionState

INTERVAL_DAYS = [1, 3, 7, 14, 30]


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
