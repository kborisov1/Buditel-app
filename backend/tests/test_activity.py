from datetime import UTC, date, datetime
from typing import Any

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.test import Client

from apps.accounts.tools import reset_progress, shift_date
from apps.activity.log import log_event
from apps.activity.models import ActivityLog
from apps.content.models import Entry, Track, TrackEntry
from apps.core.models import AppSetting
from apps.gamification.models import XpEvent
from apps.progress.models import EntryProgress, QuestionState
from apps.quizzes.models import Question, QuizAttempt

NOW = datetime(2026, 3, 10, 9, tzinfo=UTC)
PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def frozen_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("apps.core.clock.now", lambda user=None: NOW)


@pytest.fixture
def user(db: None) -> User:
    return User.objects.create_user("learner", email="learner@example.com", password=PASSWORD)


@pytest.fixture
def client(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def owner(db: None) -> User:
    return User.objects.create_superuser("owner", "owner@example.com", "pw")


@pytest.fixture
def admin_client(owner: User) -> Client:
    client = Client()
    client.force_login(owner)
    return client


def _types(user: User | None = None) -> list[str]:
    rows = ActivityLog.objects.order_by("id")
    if user is not None:
        rows = rows.filter(user=user)
    return list(rows.values_list("event_type", flat=True))


def test_log_event(user: User) -> None:
    row = log_event("user", "something", user, when=date(2026, 1, 1), n=1)
    row.refresh_from_db()
    assert (row.user, row.category, row.timestamp) == (user, "user", NOW)
    assert row.details == {"when": "2026-01-01", "n": 1}
    assert log_event("user", "anonymous", AnonymousUser()).user is None


# User activity


def _login(client: Client, password: str = PASSWORD) -> int:
    client.get("/api/auth/csrf")
    return client.post(
        "/api/auth/login",
        {"email": "learner@example.com", "password": password},
        content_type="application/json",
    ).status_code


def test_login_logout_and_daily_activity(user: User) -> None:
    client = Client()
    assert _login(client, "wrong") == 401
    assert _login(client) == 200
    client.get("/api/auth/me")
    client.post("/api/auth/logout")
    # A new account's first active day gives no login XP (scope 6.1).
    assert _types() == ["login_failed", "login", "daily_activity", "logout"]
    failed = ActivityLog.objects.get(event_type="login_failed")
    assert failed.user is None and failed.details == {"email": "learner@example.com"}


def test_returning_login_xp_is_logged(user: User) -> None:
    user.profile.last_active_local_date = date(2026, 3, 9)
    user.profile.save()
    client = Client()
    _login(client)
    client.get("/api/auth/me")
    award = ActivityLog.objects.get(event_type="xp_award")
    assert award.details == {"kind": "daily_login", "amount": 5, "reference": "login:2026-03-10"}


def test_quiz_flow_is_logged(client: Client, user: User) -> None:
    entry = Entry.objects.create(
        type=Entry.Type.EVENT,
        slug="a",
        title="a",
        summary="x",
        event_date=date(1800, 1, 1),
        importance=Entry.Importance.MAJOR,
        status=Entry.Status.PUBLISHED,
    )
    TrackEntry.objects.create(track=Track.objects.get(kind="opening"), entry=entry, position=1)
    for i in range(6):
        Question.objects.create(
            entry=entry,
            type="true_false",
            prompt=str(i),
            payload={"answer": True},
            explanation="x",
        )
    client.post("/api/entries/a/finished-reading")
    quiz = client.post("/api/entries/a/quiz").json()
    answers = [{"question_id": q["id"], "answer": True} for q in quiz["questions"]]
    client.post(
        f"/api/quiz-attempts/{quiz['attempt_id']}/submit",
        {"answers": answers},
        content_type="application/json",
    )
    types = _types(user)
    assert types[types.index("finished_reading") :] == [
        "finished_reading",
        "quiz_start",
        "xp_award",
        "xp_award",
        "quiz_submit",
    ]
    submit = ActivityLog.objects.get(event_type="quiz_submit")
    assert submit.details | {"attempt": 0} == {
        "attempt": 0,
        "entry": "a",
        "score": 5,
        "total": 5,
        "passed": True,
        "xp": 50,
    }


# Content changes and errors


def test_admin_changes_are_logged(admin_client: Client, owner: User) -> None:
    setting = AppSetting.objects.get(key="finale_percentage")
    admin_client.post(f"/admin/core/appsetting/{setting.pk}/change/", {"value": "75"})
    row = ActivityLog.objects.get(category="content")
    assert (row.user, row.event_type) == (owner, "admin_change")
    assert row.details["model"] == "core.appsetting"
    assert row.details["object"] == "finale_percentage"


def test_server_errors_are_logged(user: User, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("kaboom")

    monkeypatch.setattr("apps.gamification.api.level_info", boom)
    client = Client(raise_request_exception=False)
    client.force_login(user)
    assert client.get("/api/dashboard").status_code == 500
    row = ActivityLog.objects.get(category="error")
    assert (row.event_type, row.user) == ("server_error", user)
    assert row.details["path"] == "/api/dashboard"
    assert "kaboom" in row.details["traceback"]


def test_log_admin_is_read_only(admin_client: Client, user: User) -> None:
    log_event("user", "something", user)
    page = admin_client.get("/admin/activity/activitylog/?category__exact=user")
    assert page.status_code == 200 and "something" in page.content.decode()
    assert admin_client.get("/admin/activity/activitylog/add/").status_code == 403


# Admin tools (scope 9)


def _progress(user: User) -> None:
    entry = Entry.objects.create(type=Entry.Type.CONCEPT, slug="c", title="c", summary="x")
    question = Question.objects.create(
        entry=entry, type="true_false", prompt="?", payload={"answer": True}, explanation="x"
    )
    EntryProgress.objects.create(user=user, entry=entry, state="read", finished_reading_at=NOW)
    QuestionState.objects.create(
        user=user, question=question, due_date=NOW.date(), last_answered_at=NOW
    )
    QuizAttempt.objects.create(user=user, entry=entry, started_at=NOW)
    XpEvent.objects.create(
        user=user, kind="review", amount=2, local_date=NOW.date(), created_at=NOW
    )
    user.profile.current_streak, user.profile.longest_streak = 4, 9
    user.profile.completed_entries_count = 3
    user.profile.time_zone, user.profile.date_offset_days = "Europe/Sofia", 2
    user.profile.save()


def test_reset_progress(user: User, owner: User) -> None:
    other = User.objects.create_user("other", password="pw")
    _progress(user)
    XpEvent.objects.create(
        user=other, kind="review", amount=2, local_date=NOW.date(), created_at=NOW
    )
    reset_progress(user, by=owner)
    assert not EntryProgress.objects.filter(user=user).exists()
    assert not QuestionState.objects.filter(user=user).exists()
    assert not QuizAttempt.objects.filter(user=user).exists()
    assert not XpEvent.objects.filter(user=user).exists()
    assert XpEvent.objects.filter(user=other).exists()
    user.profile.refresh_from_db()
    profile = user.profile
    assert (profile.current_streak, profile.longest_streak, profile.completed_entries_count) == (
        0,
        0,
        0,
    )
    assert (profile.time_zone, profile.date_offset_days) == ("Europe/Sofia", 2)
    log = ActivityLog.objects.get(event_type="admin_reset_progress")
    assert (log.user, log.details) == (user, {"by": "owner"})


def test_shift_date(user: User, owner: User) -> None:
    assert shift_date(user, 3, by=owner) == 3
    assert shift_date(user, 1, by=owner) == 4
    for days in [0, -1, 366]:
        with pytest.raises(ValueError):
            shift_date(user, days, by=owner)
    assert ActivityLog.objects.filter(event_type="admin_shift_date").count() == 2


def _action(admin_client: Client, user: User, action: str, **extra: str) -> Any:
    return admin_client.post(
        "/admin/auth/user/", {"action": action, "_selected_action": [user.pk], **extra}
    )


def test_admin_reset_action_asks_first(admin_client: Client, user: User) -> None:
    _progress(user)
    page = _action(admin_client, user, "reset_progress_action")
    assert page.status_code == 200 and "learner@example.com" in page.content.decode()
    assert EntryProgress.objects.filter(user=user).exists()
    assert _action(admin_client, user, "reset_progress_action", confirm="yes").status_code == 302
    assert not EntryProgress.objects.filter(user=user).exists()


def test_admin_shift_action(admin_client: Client, user: User) -> None:
    page = _action(admin_client, user, "shift_date_action")
    assert 'name="days"' in page.content.decode()
    _action(admin_client, user, "shift_date_action", confirm="yes", days="7")
    _action(admin_client, user, "shift_date_action", confirm="yes", days="abc")
    user.profile.refresh_from_db()
    assert user.profile.date_offset_days == 7
