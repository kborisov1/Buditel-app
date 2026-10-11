"""Admin test tools (scope 9): reset a user's progress, shift their date forward."""

from django.contrib.auth.models import User
from django.db import transaction

from apps.activity.log import log_event
from apps.gamification.models import XpEvent
from apps.progress.models import EntryProgress, OlderEventCheck, QuestionState
from apps.quizzes.models import DailyChallenge, QuizAttempt

from .models import Profile

MAX_SHIFT_DAYS = 365


def reset_progress(user: User, by: User) -> None:
    """Remove all learner state. The account, time zone and date offset stay."""
    with transaction.atomic():
        EntryProgress.objects.filter(user=user).delete()
        QuestionState.objects.filter(user=user).delete()
        QuizAttempt.objects.filter(user=user).delete()
        OlderEventCheck.objects.filter(user=user).delete()
        DailyChallenge.objects.filter(user=user).delete()
        XpEvent.objects.filter(user=user).delete()
        Profile.objects.filter(user=user).update(
            current_streak=0,
            longest_streak=0,
            freezes_held=0,
            last_active_local_date=None,
            completed_entries_count=0,
        )
        log_event("user", "admin_reset_progress", user, by=by.username)


def shift_date(user: User, days: int, by: User) -> int:
    """Move the user's clock forward (architecture 7). Returns the new total offset."""
    if not 1 <= days <= MAX_SHIFT_DAYS:
        raise ValueError(f"Shift by 1 to {MAX_SHIFT_DAYS} days.")
    with transaction.atomic():
        profile = Profile.objects.select_for_update().get(user=user)
        profile.date_offset_days += days
        profile.save(update_fields=["date_offset_days"])
        log_event(
            "user",
            "admin_shift_date",
            user,
            by=by.username,
            days=days,
            offset=profile.date_offset_days,
        )
    return profile.date_offset_days
