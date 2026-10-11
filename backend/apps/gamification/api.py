"""Dashboard aggregate and profile (architecture 4, scope 7.1, 7.6)."""

from datetime import datetime
from typing import Literal, cast

from django.contrib.auth.models import User
from django.http import HttpRequest
from ninja import Router, Schema

from apps.core import clock
from apps.core.app_settings import get_setting
from apps.progress.review import due_count
from apps.progress.stats import result_history, track_progress

from .levels import level_info
from .streaks import MAX_FREEZES
from .xp import total_xp, xp_on

router = Router(tags=["dashboard"])


def _user(request: HttpRequest) -> User:
    return cast(User, request.user)


def _streak(user: User) -> "StreakOut":
    profile = user.profile
    return StreakOut(
        current=profile.current_streak,
        longest=profile.longest_streak,
        freezes_held=profile.freezes_held,
        max_freezes=MAX_FREEZES,
    )


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
    user = _user(request)
    today = clock.now(user).date()
    target, earned = get_setting("daily_goal_xp"), xp_on(user, today)
    level = level_info(total_xp(user))
    return DashboardOut(
        goal=GoalOut(target=target, earned_today=earned, reached=earned >= target),
        streak=_streak(user),
        level=LevelOut(**level.__dict__),
        reviews_due=due_count(user, today),
    )


class TrackProgressOut(Schema):
    id: int
    name: str
    kind: str
    read: int
    total: int


class HistoryEntryOut(Schema):
    slug: str
    title: str


class HistoryItemOut(Schema):
    kind: Literal["quiz", "check"]
    at: datetime
    score: int
    total: int
    passed: bool | None
    xp_awarded: int
    entry: HistoryEntryOut | None


class ProfileOut(Schema):
    email: str
    level: LevelOut
    streak: StreakOut
    tracks: list[TrackProgressOut]
    history: list[HistoryItemOut]


@router.get("/profile", response=ProfileOut, tags=["profile"])
def profile(request: HttpRequest) -> ProfileOut:
    user = _user(request)
    return ProfileOut(
        email=user.email,
        level=LevelOut(**level_info(total_xp(user)).__dict__),
        streak=_streak(user),
        tracks=[
            TrackProgressOut(
                id=p.track.pk, name=p.track.name, kind=p.track.kind, read=p.read, total=p.total
            )
            for p in track_progress(user)
        ],
        history=[
            HistoryItemOut(
                kind=i.kind,
                at=i.at,
                score=i.score,
                total=i.total,
                passed=i.passed,
                xp_awarded=i.xp_awarded,
                entry=HistoryEntryOut(slug=i.entry.slug, title=i.entry.title) if i.entry else None,
            )
            for i in result_history(user)
        ],
    )
