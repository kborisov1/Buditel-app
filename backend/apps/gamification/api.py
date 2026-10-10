"""Dashboard aggregate (architecture 4, scope 7.1)."""

from typing import cast

from django.contrib.auth.models import User
from django.http import HttpRequest
from ninja import Router, Schema

from apps.core import clock
from apps.core.app_settings import get_setting
from apps.progress.review import due_count

from .levels import level_info
from .streaks import MAX_FREEZES
from .xp import total_xp, xp_on

router = Router(tags=["dashboard"])


class GoalOut(Schema):
    target: int
    earned_today: int
    reached: bool


class StreakOut(Schema):
    current: int
    longest: int
    freezes_held: int
    max_freezes: int


class LevelOut(Schema):
    level: int
    title: str
    total_xp: int
    xp_into_level: int
    xp_for_next_level: int


class DashboardOut(Schema):
    goal: GoalOut
    streak: StreakOut
    level: LevelOut
    reviews_due: int


@router.get("/dashboard", response=DashboardOut)
def dashboard(request: HttpRequest) -> DashboardOut:
    user = cast(User, request.user)
    profile = user.profile
    today = clock.now(user).date()
    target, earned = get_setting("daily_goal_xp"), xp_on(user, today)
    level = level_info(total_xp(user))
    return DashboardOut(
        goal=GoalOut(target=target, earned_today=earned, reached=earned >= target),
        streak=StreakOut(
            current=profile.current_streak,
            longest=profile.longest_streak,
            freezes_held=profile.freezes_held,
            max_freezes=MAX_FREEZES,
        ),
        level=LevelOut(**level.__dict__),
        reviews_due=due_count(user, today),
    )
