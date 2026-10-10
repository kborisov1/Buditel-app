"""The "Start today's session" queue (scope 7.1): due reviews, an open older-event check, then
the next entries, with a planned check where the next milestone falls."""

from dataclasses import dataclass

from django.contrib.auth.models import User

from apps.accounts.models import Profile
from apps.content.library import published_entries
from apps.content.models import Entry
from apps.core import clock

from .models import EntryProgress
from .older_check import CHECK_EVERY, pending_check
from .reading import progress_states
from .review import due_count
from .unlock import unlocked_entry_ids

SESSION_ENTRIES = 3


@dataclass(frozen=True)
class Step:
    kind: str  # "review", "check" or "entry"
    count: int = 0
    check_id: int | None = None  # None for a planned check
    entry: Entry | None = None
    progress: str | None = None


def next_entries(user: User, limit: int = SESSION_ENTRIES) -> list[tuple[Entry, str | None]]:
    """Entries already started first, then unlocked unread events in timeline order."""
    unlocked = unlocked_entry_ids(user)
    states = progress_states(user)
    open_entries = published_entries().filter(pk__in=unlocked)
    started = [e for e in open_entries if states.get(e.pk) == EntryProgress.State.IN_PROGRESS]
    unread = [e for e in open_entries.filter(type=Entry.Type.EVENT) if e.pk not in states]
    return [(e, states.get(e.pk)) for e in [*started, *unread][:limit]]


def build_session(user: User) -> list[Step]:
    steps: list[Step] = []
    reviews = due_count(user, clock.now(user).date())
    if reviews:
        steps.append(Step("review", count=reviews))
    check = pending_check(user)
    if check is not None:
        steps.append(Step("check", check_id=check.pk))

    completed = Profile.objects.get(user=user).completed_entries_count
    until_check = CHECK_EVERY - completed % CHECK_EVERY
    for n, (entry, progress) in enumerate(next_entries(user), start=1):
        steps.append(Step("entry", entry=entry, progress=progress))
        if n == until_check:
            steps.append(Step("check"))
    return steps
