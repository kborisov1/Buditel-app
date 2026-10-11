import pytest
from django.core.management import call_command

from apps.content.models import Entry, GateRequirement, TrackEntry
from apps.content.rules import MIN_QUESTIONS
from apps.quizzes.models import Question
from apps.quizzes.payloads import question_errors


@pytest.mark.django_db
def test_sample_fixture_loads_publishable_content() -> None:
    call_command("loaddata", "sample", verbosity=0)

    events = Entry.objects.filter(status=Entry.Status.PUBLISHED, type=Entry.Type.EVENT)
    assert events.count() == 6
    # The first event is published but in no track, so only five events are tracked.
    assert TrackEntry.objects.filter(entry__in=events).count() == 5
    assert GateRequirement.objects.count() == 1

    for entry in events:
        questions = Question.objects.filter(entry=entry)
        assert questions.count() >= MIN_QUESTIONS, entry.slug
        for question in questions:
            _, errors = question_errors(question.type, question.prompt, question.payload)
            assert errors == [], question.prompt
