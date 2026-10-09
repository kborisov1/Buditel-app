"""The only place the code reads the current time (architecture 7)."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser


def now(user: AbstractBaseUser | AnonymousUser | None = None) -> datetime:
    """Real UTC time plus the user's date offset, in the user's time zone.

    Falls back to plain UTC when the user has no profile yet.
    """
    profile = getattr(user, "profile", None)
    if profile is None:
        return datetime.now(UTC)
    shifted = datetime.now(UTC) + timedelta(days=profile.date_offset_days)
    return shifted.astimezone(ZoneInfo(profile.time_zone))
