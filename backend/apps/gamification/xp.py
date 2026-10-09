"""XP awards (scope 6.1, architecture 6.5)."""

from django.contrib.auth.models import User

from apps.core import clock

from .models import XpEvent


def award(user: User, kind: XpEvent.Kind, amount: int, reference: str = "") -> XpEvent:
    """Write one ledger row on the user's local date."""
    now = clock.now(user)
    return XpEvent.objects.create(
        user=user,
        kind=kind,
        amount=amount,
        local_date=now.date(),
        reference=reference,
        created_at=now,
    )
