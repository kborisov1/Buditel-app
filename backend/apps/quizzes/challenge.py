"""Daily challenge (scope 6.5, architecture 6.7): a fixed set from the user's weakest read
entries, created on the first request of the local day and answered one by one."""

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from django.contrib.auth.models import User
from django.db import transaction

from apps.activity.log import log_event
from apps.core import clock
from apps.core.app_settings import get_setting
from apps.gamification import xp
from apps.gamification.models import XpEvent
from apps.progress.review import missed_question_ids, record_miss
from apps.progress.unlock import read_entry_ids, unlocked_entry_ids

from .grading import answer_error, is_correct
from .models import DailyChallenge, DailyChallengeQuestion, Question
from .weak_topics import entry_weakness

CHALLENGE_SIZE = 10


class NotInChallenge(Exception):
    """Not an unanswered question of today's challenge."""


class InvalidAnswer(Exception):
    pass


def pick_questions(user: User, rng: random.Random) -> list[int]:
    """Weakest read entries first, taking one question from each in turn (questions the user
    missed before come first), then filling from the other read entries at random."""
    pool = read_entry_ids(user) & unlocked_entry_ids(user)
    by_entry: dict[int, list[int]] = defaultdict(list)
    for question_id, entry_id in Question.objects.filter(entry_id__in=pool).values_list(
        "id", "entry_id"
    ):
        by_entry[entry_id].append(question_id)
    missed = missed_question_ids(user, [q for qs in by_entry.values() for q in qs])
    for questions in by_entry.values():
        rng.shuffle(questions)
        questions.sort(key=lambda q: q not in missed)  # stable: missed first, rest shuffled

    weakness = entry_weakness(user)
    weak = sorted((e for e in by_entry if weakness.get(e, 0) > 0), key=lambda e: (-weakness[e], e))
    chosen: list[int] = []
    queues = [list(by_entry[e]) for e in weak]
    while len(chosen) < CHALLENGE_SIZE and any(queues):
        for queue in queues:
            if queue and len(chosen) < CHALLENGE_SIZE:
                chosen.append(queue.pop(0))

    rest = [q for e, qs in by_entry.items() if e not in weak for q in qs]
    rng.shuffle(rest)
    return chosen + rest[: CHALLENGE_SIZE - len(chosen)]


def todays_challenge(user: User, rng: random.Random | None = None) -> DailyChallenge | None:
    """Today's challenge, created on first request. None while the user has nothing read."""
    now = clock.now(user)
    existing = DailyChallenge.objects.filter(user=user, local_date=now.date()).first()
    if existing is not None:
        return existing
    chosen = pick_questions(user, rng or random.Random())
    if not chosen:
        return None
    with transaction.atomic():
        challenge, created = DailyChallenge.objects.get_or_create(
            user=user, local_date=now.date(), defaults={"created_at": now}
        )
        if created:
            DailyChallengeQuestion.objects.bulk_create(
                DailyChallengeQuestion(challenge=challenge, question_id=q, position=i)
                for i, q in enumerate(chosen, start=1)
            )
    return challenge


@dataclass(frozen=True)
class ChallengeResult:
    question: Question
    correct: bool
    xp_awarded: int
    completed: bool
    bonus_xp: int


def answer_challenge(user: User, question_id: int, answer: Any) -> ChallengeResult:
    """Grade one answer of today's challenge. Misses go to review; answering the last
    question completes the challenge and awards the bonus."""
    now = clock.now(user)
    with transaction.atomic():
        challenge = (
            DailyChallenge.objects.select_for_update()
            .filter(user=user, local_date=now.date())
            .first()
        )
        item = (
            challenge.items.select_related("question")
            .filter(question_id=question_id, answered_at__isnull=True)
            .first()
            if challenge
            else None
        )
        if challenge is None or item is None:
            raise NotInChallenge
        question = item.question
        error = answer_error(question.type, answer)
        if error:
            raise InvalidAnswer(error)

        item.answer, item.answered_at = answer, now
        item.correct = is_correct(question.type, question.payload, answer)
        item.save(update_fields=["answer", "correct", "answered_at"])
        reference = f"challenge:{challenge.pk}"
        gained = 0
        if item.correct:
            event = xp.award(
                user, XpEvent.Kind.DAILY_CHALLENGE, get_setting("xp_challenge_correct"), reference
            )
            gained = event.amount if event else 0
        else:
            record_miss(user, question_id)

        bonus = 0
        completed = not challenge.items.filter(answered_at__isnull=True).exists()
        if completed:
            challenge.completed_at = now
            challenge.save(update_fields=["completed_at"])
            event = xp.award(
                user,
                XpEvent.Kind.DAILY_CHALLENGE,
                get_setting("xp_challenge_bonus"),
                f"{reference}:bonus",
            )
            bonus = event.amount if event else 0
        log_event(
            "user",
            "challenge_answer",
            user,
            challenge=challenge.pk,
            question=question_id,
            correct=item.correct,
            completed=completed,
        )
    return ChallengeResult(question, bool(item.correct), gained, completed, bonus)
