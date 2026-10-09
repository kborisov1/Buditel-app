from datetime import UTC, datetime
from types import SimpleNamespace

from apps.core import clock


def test_now_without_user_is_utc() -> None:
    assert clock.now().tzinfo == UTC


def test_now_applies_offset_and_time_zone() -> None:
    profile = SimpleNamespace(date_offset_days=2, time_zone="Europe/Sofia")
    user = SimpleNamespace(profile=profile)
    shifted = clock.now(user)  # type: ignore[arg-type]
    assert shifted.tzinfo is not None
    assert shifted.utcoffset() is not None
    assert (shifted - datetime.now(UTC)).days >= 1
