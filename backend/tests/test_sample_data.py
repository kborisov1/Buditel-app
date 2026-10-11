import re

import pytest
from django.core.management import call_command

from apps.content.models import Entry, GateRequirement, Phase, TrackEntry
from apps.content.rules import MIN_QUESTIONS
from apps.progress.graph_check import analyse
from apps.progress.unlock import load_graph, unlocked_ids
from apps.quizzes.models import Question
from apps.quizzes.payloads import question_errors

PHASE_ENTRY_PKS = [106, 107, 108, 109, 110]
YEAR = re.compile(r"\((\d{4})\)")


def _id(slug: str) -> int:
    return Entry.objects.get(slug=slug).pk


@pytest.mark.django_db
def test_sample_fixture_loads_publishable_content() -> None:
    call_command("loaddata", "sample", verbosity=0)

    events = Entry.objects.filter(status=Entry.Status.PUBLISHED, type=Entry.Type.EVENT)
    assert events.count() == 11
    assert TrackEntry.objects.filter(entry__in=events).count() == 11
    assert GateRequirement.objects.count() == 1

    for entry in events:
        questions = Question.objects.filter(entry=entry)
        assert questions.count() >= MIN_QUESTIONS, entry.slug
        for question in questions:
            _, errors = question_errors(question.type, question.prompt, question.payload)
            assert errors == [], question.prompt


@pytest.mark.django_db
def test_sample_phase_events_fall_in_phase() -> None:
    call_command("loaddata", "sample", verbosity=0)

    phase = Phase.objects.get(name="Пробуждане")
    for entry in Entry.objects.filter(pk__in=PHASE_ENTRY_PKS):
        assert entry.event_date is not None
        assert phase.start_date <= entry.event_date <= phase.end_date, entry.slug


@pytest.mark.django_db
def test_sample_date_ordering_is_chronological() -> None:
    call_command("loaddata", "sample", verbosity=0)

    for question in Question.objects.filter(type="date_ordering"):
        items = question.payload["items"]
        years = [int(YEAR.findall(item)[0]) for item in items]
        assert years == sorted(years), items


@pytest.mark.django_db
def test_sample_track_events_are_chronological() -> None:
    call_command("loaddata", "sample", verbosity=0)

    for track_id in TrackEntry.objects.values_list("track_id", flat=True).distinct():
        dates = [
            item.entry.event_date
            for item in TrackEntry.objects.filter(track_id=track_id)
        ]
        known = [d for d in dates if d is not None]
        assert len(known) == len(dates), track_id
        assert known == sorted(known), track_id


@pytest.mark.django_db
def test_sample_unlock_starts_with_awakening_track() -> None:
    call_command("loaddata", "sample", verbosity=0)
    graph = load_graph()

    # Scope 3.2: a new reader starts in the Awakening track, which opens with its first event.
    paisius = _id("napisvane-na-istoriya-slavyanoblgarska")
    assert unlocked_ids(graph, set()) == {paisius}


@pytest.mark.django_db
def test_sample_unlock_opens_other_tracks_after_awakening() -> None:
    call_command("loaddata", "sample", verbosity=0)
    graph = load_graph()

    # Scope 3.2: the other tracks open once all Awakening events are read. Each track then
    # opens with its first event, and later events stay locked until the one before is read.
    awakening = {
        _id("napisvane-na-istoriya-slavyanoblgarska"),
        _id("nedelnik-sofronii"),
    }
    first_events = {
        _id("svetsko-uchilishte-gabrovo"),
        _id("ohridska-arhiepiskopiya-ukinata"),
        _id("kyuchuk-kaynardzhiyski-mir"),
    }
    assert unlocked_ids(graph, awakening) == awakening | first_events


@pytest.mark.django_db
def test_sample_unlock_graph_has_no_blocking_problems() -> None:
    # Scope 3.4: every published entry must be reachable by a learner.
    call_command("loaddata", "sample", verbosity=0)
    graph = load_graph()

    report = analyse(graph, {})
    assert [i for i in report.issues if i.blocking] == []
    assert report.reachable == graph.events | graph.others
