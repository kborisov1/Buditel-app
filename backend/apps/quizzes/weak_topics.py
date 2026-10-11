"""Weak topics (scope 6.6, architecture 6.7): per-entry weakness from the user's answers."""

from collections import defaultdict
from datetime import datetime

from django.contrib.auth.models import User

from apps.core import clock
from apps.progress.models import OlderEventCheckQuestion

from .models import DailyChallengeQuestion, QuizAttemptQuestion

HALF_LIFE_DAYS = 14


def entry_weakness(user: User) -> dict[int, float]:
    """Recency-weighted miss rate per entry, from 0 (no misses) to 1 (all missed).

    Uses graded quiz, older-event-check and daily-challenge answers. Each answer's weight
    halves every HALF_LIFE_DAYS, so recent misses count more.
    """
    answers: list[tuple[int, bool | None, datetime | None]] = [
        *QuizAttemptQuestion.objects.filter(attempt__user=user, correct__isnull=False).values_list(
            "question__entry_id", "correct", "attempt__submitted_at"
        ),
        *OlderEventCheckQuestion.objects.filter(
            older_check__user=user, correct__isnull=False
        ).values_list("question__entry_id", "correct", "older_check__submitted_at"),
        *DailyChallengeQuestion.objects.filter(
            challenge__user=user, correct__isnull=False
        ).values_list("question__entry_id", "correct", "answered_at"),
    ]
    now = clock.now(user)
    missed: dict[int, float] = defaultdict(float)
    total: dict[int, float] = defaultdict(float)
    for entry_id, correct, at in answers:
        if at is None:
            continue
        age_days = max(0.0, (now - at).total_seconds() / 86400)
        weight = 0.5 ** (age_days / HALF_LIFE_DAYS)
        total[entry_id] += weight
        if not correct:
            missed[entry_id] += weight
    return {entry_id: missed[entry_id] / weight for entry_id, weight in total.items() if weight}
