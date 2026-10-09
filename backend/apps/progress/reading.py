"""Reading state: the "Finished reading" step before the quiz (scope 4, architecture 6.2)."""

from django.contrib.auth.models import User

from apps.content.models import Entry
from apps.core import clock

from .models import EntryProgress
from .unlock import is_unlocked


class EntryLocked(Exception):
    """Locked entries cannot be read (scope 3.4)."""


def finish_reading(user: User, entry: Entry) -> EntryProgress:
    """Record that the user finished reading, which enables the quiz.

    Repeating it keeps the first timestamp and never downgrades a read entry.
    """
    if not is_unlocked(user, entry.pk):
        raise EntryLocked
    progress, _ = EntryProgress.objects.get_or_create(
        user=user,
        entry=entry,
        defaults={"state": EntryProgress.State.IN_PROGRESS, "finished_reading_at": clock.now(user)},
    )
    return progress


def progress_states(user: User) -> dict[int, str]:
    """The user's progress state by entry ID. Entries without progress are absent."""
    rows = EntryProgress.objects.filter(user=user).values_list("entry_id", "state")
    return dict(rows)
