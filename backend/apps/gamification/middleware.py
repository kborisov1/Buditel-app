from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from apps.core import clock

from .streaks import record_daily_activity


class DailyActivityMiddleware:
    """Runs the streak and login-XP check on the first API request of the user's local day
    (architecture 6.5, 6.6). No scheduler is involved."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = request.user
        if request.path.startswith("/api/") and user.is_authenticated:
            profile = getattr(user, "profile", None)
            today = clock.now(user).date()
            if profile is not None and profile.last_active_local_date != today:
                if record_daily_activity(user):
                    profile.refresh_from_db()  # the view sees the updated streak
        return self.get_response(request)
