from datetime import UTC, date, datetime, timedelta

import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.content.models import Entry
from apps.core.app_settings import get_setting
from apps.core.models import AppSetting
from apps.gamification.levels import level_for, level_info, title_for, xp_to_reach
from apps.gamification.models import XpEvent
from apps.gamification.streaks import Streak, advance
from apps.gamification.xp import award, xp_on
from apps.progress.models import QuestionState
from apps.quizzes.models import Question

# Levels (scope 6.2)


@pytest.mark.parametrize(
    ("xp", "level"), [(0, 1), (99, 1), (100, 2), (224, 2), (225, 3), (374, 3), (375, 4)]
)
def test_level_boundaries(xp: int, level: int) -> None:
    assert level_for(xp, 100, 25) == level


@pytest.mark.parametrize(("base", "step"), [(100, 25), (40, 0), (10, 100), (1, 1), (7, 3)])
def test_closed_form_matches_counting(base: int, step: int) -> None:
    level = 1
    for xp in range(0, 20000, 7):
        while xp_to_reach(level + 1, base, step) <= xp:
            level += 1
        assert level_for(xp, base, step) == level


@pytest.mark.parametrize(
    ("level", "title"),
    [
        (1, "peasant"),
        (2, "peasant"),
        (3, "student"),
        (5, "student"),
        (6, "teacher"),
        (11, "reading_room_activist"),
        (12, "haidut"),
        (17, "komita"),
        (20, "voivode"),
        (21, "apostle"),
        (60, "apostle"),
    ],
)
def test_titles(level: int, title: str) -> None:
    assert title_for(level) == title


@pytest.mark.django_db
def test_level_info_progress() -> None:
    info = level_info(150)
    assert (info.level, info.title, info.xp_into_level, info.xp_for_next_level) == (
        2,
        "peasant",
        50,
        125,
    )


@pytest.mark.django_db
def test_level_curve_from_settings() -> None:
    AppSetting.objects.filter(key="level_base_xp").update(value=50)
    assert level_info(60).level == 2


# Streaks (scope 6.3)

D = date(2026, 3, 10)


def _streak(
    current: int = 0, freezes: int = 0, last: date | None = None, longest: int = 0
) -> Streak:
    return Streak(current, max(longest, current), freezes, last)


def test_first_day_starts_streak() -> None:
    assert advance(_streak(), D) == Streak(1, 1, 0, D)


def test_same_or_earlier_day_changes_nothing() -> None:
    s = _streak(3, last=D)
    assert advance(s, D) is s
    assert advance(s, D - timedelta(days=1)) is s


def test_consecutive_day_extends() -> None:
    assert advance(_streak(3, last=D), D + timedelta(days=1)).current == 4


@pytest.mark.parametrize(("missed", "freezes", "left"), [(1, 1, 0), (1, 2, 1), (2, 2, 0)])
def test_freezes_cover_missed_days(missed: int, freezes: int, left: int) -> None:
    after = advance(_streak(3, freezes, D), D + timedelta(days=missed + 1))
    assert (after.current, after.freezes) == (4, left)


@pytest.mark.parametrize(("missed", "freezes"), [(1, 0), (3, 2)])
def test_gap_too_long_resets_and_keeps_freezes(missed: int, freezes: int) -> None:
    after = advance(_streak(5, freezes, D, longest=9), D + timedelta(days=missed + 1))
    assert (after.current, after.freezes, after.longest) == (1, freezes, 9)


def test_freeze_earned_every_seven_days_capped_at_two() -> None:
    s = _streak()
    held = []
    for day in range(21):
        s = advance(s, D + timedelta(days=day))
        held.append(s.freezes)
    assert held[5] == 0 and held[6] == 1 and held[13] == 2 and held[20] == 2
    assert s.longest == 21


# XP and the daily goal (scope 6.1, 6.4)

NOW = datetime(2026, 3, 10, 9, tzinfo=UTC)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> list[datetime]:
    current = [NOW]
    monkeypatch.setattr("apps.core.clock.now", lambda user=None: current[0])
    return current


@pytest.fixture
def user(db: None) -> User:
    return User.objects.create_user("learner", password="pw")


def _kinds(user: User) -> list[tuple[str, int]]:
    return [(e.kind, e.amount) for e in XpEvent.objects.filter(user=user).order_by("id")]


def test_goal_bonus_once_then_reduced_rate(user: User, clock: list[datetime]) -> None:
    award(user, XpEvent.Kind.REVIEW, 30)
    award(user, XpEvent.Kind.REVIEW, 10)  # reaches 40
    award(user, XpEvent.Kind.REVIEW, 5)
    award(user, XpEvent.Kind.REVIEW, 3)
    assert _kinds(user) == [
        ("review", 30),
        ("review", 10),
        ("daily_goal_bonus", 10),
        ("review", 4),
        ("review", 2),
    ]
    assert xp_on(user, NOW.date()) == 56


def test_award_reaching_goal_is_full_value(user: User, clock: list[datetime]) -> None:
    event = award(user, XpEvent.Kind.QUIZ_FIRST_PASS, 50)
    assert event is not None and event.amount == 50
    assert ("daily_goal_bonus", 10) in _kinds(user)


def test_goal_resets_next_local_day(user: User, clock: list[datetime]) -> None:
    award(user, XpEvent.Kind.QUIZ_FIRST_PASS, 50)
    clock[0] = NOW + timedelta(days=1)
    event = award(user, XpEvent.Kind.REVIEW, 5)
    assert event is not None and (event.amount, event.local_date) == (5, date(2026, 3, 11))


def test_goal_settings(user: User, clock: list[datetime]) -> None:
    AppSetting.objects.filter(key="daily_goal_xp").update(value=5)
    AppSetting.objects.filter(key="goal_overflow_percentage").update(value=50)
    AppSetting.objects.filter(key="xp_daily_goal_bonus").update(value=0)
    award(user, XpEvent.Kind.REVIEW, 5)
    award(user, XpEvent.Kind.REVIEW, 4)
    assert _kinds(user) == [("review", 5), ("review", 2)]


def test_goal_and_level_settings_seeded(db: None) -> None:
    assert [
        get_setting(k)
        for k in ["daily_goal_xp", "goal_overflow_percentage", "level_base_xp", "level_step_xp"]
    ] == [40, 80, 100, 25]


# Daily activity through the API (architecture 6.5, 6.6)


@pytest.fixture
def client(user: User, clock: list[datetime]) -> Client:
    client = Client()
    client.force_login(user)
    return client


def test_first_request_of_day_records_login(
    client: Client, user: User, clock: list[datetime]
) -> None:
    client.get("/api/auth/me")
    client.get("/api/auth/me")
    assert _kinds(user) == [("daily_login", 5)]
    user.profile.refresh_from_db()
    assert (user.profile.current_streak, user.profile.last_active_local_date) == (1, NOW.date())

    clock[0] = NOW + timedelta(days=1)
    client.get("/api/auth/me")
    user.profile.refresh_from_db()
    assert user.profile.current_streak == 2
    assert _kinds(user) == [("daily_login", 5), ("daily_login", 5)]


def test_missed_day_uses_freeze(client: Client, user: User, clock: list[datetime]) -> None:
    user.profile.current_streak, user.profile.freezes_held = 6, 1
    user.profile.last_active_local_date = NOW.date() - timedelta(days=2)
    user.profile.save()
    client.get("/api/auth/me")
    user.profile.refresh_from_db()
    # The freeze covers the gap, and reaching 7 earns it back.
    assert (user.profile.current_streak, user.profile.freezes_held) == (7, 1)


def test_anonymous_and_admin_requests_skip_activity(user: User, clock: list[datetime]) -> None:
    assert Client().get("/api/auth/me").status_code == 401
    client = Client()
    client.force_login(user)
    client.get("/admin/")
    assert not XpEvent.objects.exists()


def test_dashboard(client: Client, user: User) -> None:
    entry = Entry.objects.create(type=Entry.Type.CONCEPT, slug="c", title="c", summary="x")
    for days in [-3, 0, 1]:
        question = Question.objects.create(
            entry=entry,
            type="true_false",
            prompt=f"{days}?",
            payload={"answer": True},
            explanation="x",
        )
        QuestionState.objects.create(
            user=user,
            question=question,
            due_date=NOW.date() + timedelta(days=days),
            last_answered_at=NOW,
        )
    data = client.get("/api/dashboard").json()
    assert data == {
        "goal": {"target": 40, "earned_today": 5, "reached": False},
        "streak": {"current": 1, "longest": 1, "freezes_held": 0, "max_freezes": 2},
        "level": {
            "level": 1,
            "title": "peasant",
            "total_xp": 5,
            "xp_into_level": 5,
            "xp_for_next_level": 100,
        },
        "reviews_due": 2,
    }
