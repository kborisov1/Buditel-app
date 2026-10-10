"""Login streaks and freezes (scope 6.3, architecture 6.6)."""

from dataclasses import dataclass, replace
from datetime import date

from django.contrib.auth.models import User
from django.db import transaction

from apps.accounts.models import Profile
from apps.core import clock
from apps.core.app_settings import get_setting

from . import xp
from .models import XpEvent

FREEZE_EVERY = 7
MAX_FREEZES = 2


@dataclass(frozen=True)
class Streak:
    current: int
    longest: int
    freezes: int
    last_active: date | None


def advance(streak: Streak, today: date) -> Streak:
    """Record activity on `today`, resolving any missed days first.

    Freezes are spent only when they cover every missed day; otherwise the streak resets
    and the freezes are kept.
    """
    if streak.last_active is not None and today <= streak.last_active:
        return streak
    current, freezes = streak.current, streak.freezes
    if streak.last_active is not None:
        missed = (today - streak.last_active).days - 1
        if missed > freezes:
            current = 0
        else:
            freezes -= missed
    current += 1
    if current % FREEZE_EVERY == 0:
        freezes = min(MAX_FREEZES, freezes + 1)
    return replace(
        streak,
        current=current,
        longest=max(streak.longest, current),
        freezes=freezes,
        last_active=today,
    )


def record_daily_activity(user: User) -> bool:
    """Update the streak and award login XP on the user's first activity of the local day.

    Returns whether this was the first activity today.
    """
    today = clock.now(user).date()
    with transaction.atomic():
        profile = Profile.objects.select_for_update().get(user=user)
        before = Streak(
            profile.current_streak,
            profile.longest_streak,
            profile.freezes_held,
            profile.last_active_local_date,
        )
        after = advance(before, today)
        if after == before:
            return False
        profile.current_streak = after.current
        profile.longest_streak = after.longest
        profile.freezes_held = after.freezes
        profile.last_active_local_date = after.last_active
        profile.save(
            update_fields=[
                "current_streak",
                "longest_streak",
                "freezes_held",
                "last_active_local_date",
            ]
        )
        xp.award(user, XpEvent.Kind.DAILY_LOGIN, get_setting("xp_daily_login"), f"login:{today}")
    return True
