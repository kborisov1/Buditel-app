"""Older-event check after every third completed entry (scope 4.1, architecture 6.4)."""

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from django.contrib.auth.models import User
from django.db import transaction

from apps.accounts.models import Profile
from apps.content.models import Entry
from apps.core import clock
from apps.core.app_settings import get_setting
from apps.gamification import xp
from apps.gamification.models import XpEvent
from apps.quizzes.grading import answer_set_error, is_correct
from apps.quizzes.models import Question

from .models import EntryProgress, OlderEventCheck, OlderEventCheckQuestion
from .review import record_miss
from .unlock import unlocked_entry_ids

CHECK_EVERY = 3
CHECK_SIZE = 3
MIN_SIZE = 2


class CheckClosed(Exception):
    """The check is already submitted or skipped."""


class InvalidAnswers(Exception):
    pass


def current_milestone(completed: int) -> int:
    return completed // CHECK_EVERY * CHECK_EVERY


def pending_check(user: User, rng: random.Random | None = None) -> OlderEventCheck | None:
    """The open check for the latest milestone, created on first request. Earlier unanswered
    milestones are not stacked."""
    completed = Profile.objects.get(user=user).completed_entries_count
    milestone = current_milestone(completed)
    if milestone == 0:
        return None
    with transaction.atomic():
        now = clock.now(user)
        check, created = OlderEventCheck.objects.get_or_create(
            user=user, milestone=milestone, defaults={"created_at": now}
        )
        if created:
            chosen = draw_questions(user, rng or random.Random())
            OlderEventCheckQuestion.objects.bulk_create(
                OlderEventCheckQuestion(older_check=check, question_id=q, position=i)
                for i, q in enumerate(chosen, start=1)
            )
            if not chosen:  # too little read content yet: skip this milestone
                check.submitted_at, check.score = now, 0
                check.save(update_fields=["submitted_at", "score"])
    return check if check.submitted_at is None else None


def draw_questions(user: User, rng: random.Random) -> list[int]:
    """One question from each of up to 3 read events, skipping the entries completed most
    recently. Falls back to all read events when the older ones are too few."""
    read = EntryProgress.objects.filter(
        user=user, state=EntryProgress.State.READ, entry_id__in=unlocked_entry_ids(user)
    ).order_by("-passed_at", "-id")
    recent = set(read.values_list("entry_id", flat=True)[:CHECK_EVERY])
    events = list(read.filter(entry__type=Entry.Type.EVENT).values_list("entry_id", flat=True))
    questions: dict[int, list[int]] = defaultdict(list)
    for question_id, entry_id in Question.objects.filter(entry_id__in=events).values_list(
        "id", "entry_id"
    ):
        questions[entry_id].append(question_id)

    with_questions = [e for e in events if questions[e]]
    older = [e for e in with_questions if e not in recent]
    pool = older if len(older) >= MIN_SIZE else with_questions
    if len(pool) < MIN_SIZE:
        return []
    return [rng.choice(questions[e]) for e in rng.sample(pool, min(CHECK_SIZE, len(pool)))]


def open_check(user: User, check_id: int) -> OlderEventCheck:
    check = OlderEventCheck.objects.get(pk=check_id, user=user)
    if check.submitted_at is not None:
        raise CheckClosed
    return check


@dataclass(frozen=True)
class CheckResult:
    check: OlderEventCheck
    items: list[OlderEventCheckQuestion]


def submit_check(user: User, check_id: int, answers: dict[int, Any]) -> CheckResult:
    """Grade all answers. No pass mark: XP per correct answer, misses go to review."""
    with transaction.atomic():
        check = OlderEventCheck.objects.select_for_update().get(pk=check_id, user=user)
        if check.submitted_at is not None:
            raise CheckClosed
        items = list(check.items.select_related("question"))
        error = answer_set_error([i.question for i in items], answers)
        if error:
            raise InvalidAnswers(error)

        for item in items:
            item.answer = answers[item.question_id]
            item.correct = is_correct(item.question.type, item.question.payload, item.answer)
            if not item.correct:
                record_miss(user, item.question_id)
        OlderEventCheckQuestion.objects.bulk_update(items, ["answer", "correct"])

        check.score = sum(1 for i in items if i.correct)
        check.submitted_at = clock.now(user)
        if check.score:
            event = xp.award(
                user,
                XpEvent.Kind.OLDER_EVENT_CHECK,
                check.score * get_setting("xp_check_correct"),
                f"older_check:{check.pk}",
            )
            check.xp_awarded = event.amount if event else 0
        check.save()
    return CheckResult(check, items)
