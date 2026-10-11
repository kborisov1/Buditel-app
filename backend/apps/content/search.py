"""Title search (scope 7, architecture 11): substring and trigram matches on titles."""

from django.contrib.postgres.search import TrigramWordSimilarity
from django.db.models import Case, IntegerField, Q, QuerySet, Value, When

from .library import published_entries
from .models import Entry

MIN_QUERY = 2
LIMIT = 20
# word_similarity cut-off: tolerates a typo or two in a word ("въстане" for "въстание").
MIN_SIMILARITY = 0.5


def search_titles(query: str, limit: int = LIMIT) -> QuerySet[Entry]:
    """Published entries whose title matches, best first: titles starting with the query,
    then containing it, then close matches by trigram word similarity."""
    query = " ".join(query.split())
    if len(query) < MIN_QUERY:
        return Entry.objects.none()
    return (
        published_entries()
        .annotate(similarity=TrigramWordSimilarity(query, "title"))
        .filter(Q(title__icontains=query) | Q(similarity__gte=MIN_SIMILARITY))
        .annotate(
            rank=Case(
                When(title__istartswith=query, then=Value(0)),
                When(title__icontains=query, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        .order_by("rank", "-similarity", "title")[:limit]
    )
