"""Timeline data (scope 7.2): published events in order, plus the phase bands."""

from django.db.models import QuerySet

from .library import published_entries
from .models import Entry, Phase


def timeline_events() -> QuerySet[Entry]:
    """Events in the default entry order: year, then the author's year_order, then date."""
    return published_entries().filter(type=Entry.Type.EVENT)


def phases() -> QuerySet[Phase]:
    return Phase.objects.all()
