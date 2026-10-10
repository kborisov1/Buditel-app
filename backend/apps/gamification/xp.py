"""XP awards and the daily goal (scope 6.1, 6.4, architecture 6.5)."""

from datetime import date, datetime

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum

from apps.accounts.models import Profile
from apps.core import clock
from apps.core.app_settings import get_setting

from .models import XpEvent


def xp_on(user: User, day: date) -> int:
    total = XpEvent.objects.filter(user=user, local_date=day).aggregate(s=Sum("amount"))["s"]
    return int(total or 0)


def total_xp(user: User) -> int:
    return int(XpEvent.objects.filter(user=user).aggregate(s=Sum("amount"))["s"] or 0)


def award(user: User, kind: XpEvent.Kind, amount: int, reference: str = "") -> XpEvent | None:
    """Write one ledger row on the user's local date.

    After the daily goal is reached, awards are reduced and rounded. The award that reaches
    the goal also writes the one-time goal bonus. Returns None when nothing is awarded.
    """
    with transaction.atomic():
        # Serializes a user's awards so the goal bonus is written once.
        Profile.objects.select_for_update().filter(user=user).first()
        now = clock.now(user)
        today = now.date()
        goal = get_setting("daily_goal_xp")
        earned = xp_on(user, today)
        if earned >= goal:
            amount = (amount * get_setting("goal_overflow_percentage") + 50) // 100
        if amount <= 0:
            return None
        event = _write(user, kind, amount, today, reference, now)
        bonus = get_setting("xp_daily_goal_bonus")
        if earned < goal <= earned + amount and bonus > 0:
            _write(user, XpEvent.Kind.DAILY_GOAL_BONUS, bonus, today, f"goal:{today}", now)
        return event


def _write(user: User, kind: str, amount: int, day: date, reference: str, now: datetime) -> XpEvent:
    return XpEvent.objects.create(
        user=user, kind=kind, amount=amount, local_date=day, reference=reference, created_at=now
    )
