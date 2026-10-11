"""Validation rules for authored entries (scope 1, 2.2, 2.3, 2.4, 3.2, 7.2)."""

from collections.abc import Sequence
from datetime import date

PERIOD_START = date(1762, 1, 1)
PERIOD_END = date(1878, 12, 31)
MIN_QUESTIONS = 6


def entry_field_errors(
    *, is_event: bool, event_date: date | None, importance: str, in_tracks_or_gates: bool = False
) -> dict[str, str]:
    """Return field-level errors for an entry's type-dependent fields."""
    errors: dict[str, str] = {}
    if not is_event and in_tracks_or_gates:
        errors["type"] = "Remove this entry from its tracks and gates before changing its type."
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


def publish_error(*, publishing: bool, question_count: int) -> str | None:
    """Published entries need a full question pool (scope 2.4)."""
    if publishing and question_count < MIN_QUESTIONS:
        return f"An entry needs at least {MIN_QUESTIONS} questions to be published."
    return None


def order_ties(events: Sequence[tuple[int, date | None, int]]) -> list[tuple[int, int]]:
    """Neighbouring track events, given as (id, date, year_order) in track order, whose
    order is not set by the author: same date and same year_order, so the title decides."""
    return [(a[0], b[0]) for a, b in zip(events, events[1:], strict=False) if a[1:] == b[1:]]
