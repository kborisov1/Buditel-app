"""The single helper for writing the activity log (architecture 10)."""

from typing import Any, cast

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser, User

from apps.core import clock

from .models import ActivityLog


def log_event(
    category: str,
    event_type: str,
    user: AbstractBaseUser | AnonymousUser | None = None,
    **details: Any,
) -> ActivityLog:
    """Write one log row, stamped with real UTC time (not the user's shifted clock)."""
    return ActivityLog.objects.create(
        user=cast(User, user) if user is not None and user.is_authenticated else None,
        timestamp=clock.now(),
        category=category,
        event_type=event_type,
        details=details,
    )
