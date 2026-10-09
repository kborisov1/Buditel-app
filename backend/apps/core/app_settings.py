"""Known tunables with defaults and validation, read through `get_setting`."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Spec:
    default: Any
    help: str
    is_valid: Callable[[Any], bool]
    error: str


def _int_between(low: int, high: int) -> Callable[[Any], bool]:
    return lambda v: type(v) is int and low <= v <= high


def _percentage(help: str, default: int) -> Spec:
    return Spec(default, help, _int_between(1, 100), "Enter a whole number from 1 to 100.")


def _xp(help: str, default: int) -> Spec:
    return Spec(default, help, _int_between(0, 1000), "Enter a whole number from 0 to 1000.")


SPECS: dict[str, Spec] = {
    "finale_percentage": _percentage(
        "Share of events the user must read in every track to unlock the Finale (scope 3.4).", 80
    ),
    "quiz_pass_percentage": _percentage(
        "Share of quiz questions that must be correct to pass (scope 4).", 80
    ),
    "quiz_missed_weight": Spec(
        default=3,
        help="How many times more likely a question the user missed is drawn in a quiz (scope 4).",
        is_valid=_int_between(1, 20),
        error="Enter a whole number from 1 to 20.",
    ),
    "xp_quiz_first_pass": _xp("XP for passing an entry's quiz the first time (scope 6.1).", 50),
    "xp_quiz_retake": _xp("XP for passing a quiz again after the entry is read (scope 6.1).", 5),
    "xp_review_correct": _xp("XP per correct answer in review or practice (scope 6.1).", 2),
    "xp_check_correct": _xp("XP per correct answer in an older-event check (scope 6.1).", 3),
    "xp_daily_login": _xp("XP for the first login of the day (scope 6.1).", 5),
    "xp_daily_goal_bonus": _xp("XP bonus for reaching the daily goal (scope 6.1).", 10),
}


def setting_error(key: str, value: Any) -> str | None:
    spec = SPECS.get(key)
    if spec is None:
        return f"Unknown setting: {key}."
    return None if spec.is_valid(value) else spec.error


def get_setting(key: str) -> Any:
    """The stored value, or the default when no row exists."""
    from .models import AppSetting

    row = AppSetting.objects.filter(key=key).values_list("value", flat=True).first()
    return SPECS[key].default if row is None else row
