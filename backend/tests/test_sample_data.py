import re

import pytest
from django.core.management import call_command

from apps.content.models import Entry, GateRequirement, Phase, TrackEntry
from apps.content.rules import MIN_QUESTIONS
from apps.quizzes.models import Question
from apps.quizzes.payloads import question_errors

PHASE_ENTRY_PKS = [106, 107, 108, 109, 110]
YEAR = re.compile(r"\((\d{4})\)")


@pytest.mark.django_db
def test_sample_fixture_loads_publishable_content() -> None:
    call_command("loaddata", "sample", verbosity=0)

    events = Entry.objects.filter(status=Entry.Status.PUBLISHED, type=Entry.Type.EVENT)
    assert events.count() == 11
    # Six events (the draft Paisius event and the five Пробуждане events) are in no track.
    assert TrackEntry.objects.filter(entry__in=events).count() == 5
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
