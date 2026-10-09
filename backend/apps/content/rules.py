"""Validation rules for authored entries (scope 1, 2.2, 2.3, 7.2)."""

from datetime import date

PERIOD_START = date(1762, 1, 1)
PERIOD_END = date(1878, 12, 31)


def entry_field_errors(
    *, is_event: bool, event_date: date | None, importance: str
) -> dict[str, str]:
    """Return field-level errors for an entry's type-dependent fields."""
    errors: dict[str, str] = {}
    if is_event:
        if event_date is None:
            errors["event_date"] = "Events need a date (best guess if not exact)."
        elif not PERIOD_START <= event_date <= PERIOD_END:
            errors["event_date"] = "Events must fall within 1762-1878."
        if not importance:
            errors["importance"] = "Events need an importance level."
    elif importance:
        errors["importance"] = "Importance applies to events only."
    return errors
