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


SPECS: dict[str, Spec] = {
    "finale_percentage": Spec(
        default=80,
        help="Share of events the user must read in every track to unlock the Finale (scope 3.4).",
        is_valid=lambda v: type(v) is int and 1 <= v <= 100,
        error="Enter a whole number from 1 to 100.",
    ),
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
