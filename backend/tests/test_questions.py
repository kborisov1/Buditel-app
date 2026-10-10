from datetime import date
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client

from apps.content.models import Entry
from apps.content.rules import publish_error
from apps.quizzes.forms import QuestionForm
from apps.quizzes.models import Question
from apps.quizzes.payloads import question_errors
from tests.helpers import EMPTY_INLINES


@pytest.mark.parametrize(
    ("qtype", "prompt", "payload"),
    [
        ("multiple_choice", "Кой?", {"options": ["А", "Б"], "correct": 1}),
        ("true_false", "Вярно ли е?", {"answer": False}),
        ("date_ordering", "Подредете.", {"items": ["А", "Б", "В"]}),
        ("fill_blank", "Паисий пише през ___ г.", {"answers": ["1762"]}),
    ],
)
def test_valid_payloads(qtype: str, prompt: str, payload: dict[str, Any]) -> None:
    normalized, errors = question_errors(qtype, prompt, payload)
    assert errors == []
    assert normalized == payload


@pytest.mark.parametrize(
    ("qtype", "prompt", "payload", "message"),
    [
        ("multiple_choice", "?", {"options": ["А"], "correct": 0}, "between 2 and 6"),
        ("multiple_choice", "?", {"options": ["А", "Б"], "correct": None}, "marked correct"),
        ("multiple_choice", "?", {"options": ["А", "Б"], "correct": 2}, "out of range"),
        ("multiple_choice", "?", {"options": ["А", "а"], "correct": 0}, "unique"),
        ("true_false", "?", {"answer": None}, "true or false"),
        ("date_ordering", "?", {"items": ["А", "Б"]}, "between 3 and 6"),
        ("date_ordering", "?", {"items": ["А", " ", "В"]}, "cannot be empty"),
        ("fill_blank", "Без празно", {"answers": ["x"]}, "exactly one blank"),
        ("fill_blank", "___ и ___", {"answers": ["x"]}, "exactly one blank"),
        ("fill_blank", "___", {"answers": []}, "between 1 and 10"),
        ("true_false", "?", {"answer": True, "extra": 1}, "Extra inputs"),
        ("matching", "?", {}, "Unknown question type"),
    ],
)
def test_invalid_payloads(qtype: str, prompt: str, payload: dict[str, Any], message: str) -> None:
    _, errors = question_errors(qtype, prompt, payload)
    assert any(message in e for e in errors), errors


def test_publish_needs_six_questions() -> None:
    assert publish_error(publishing=True, question_count=5)
    assert publish_error(publishing=True, question_count=6) is None
    assert publish_error(publishing=False, question_count=0) is None


@pytest.fixture
def entry(db: None) -> Entry:
    return Entry.objects.create(
        type=Entry.Type.EVENT,
        slug="istoriya",
        title="История славянобългарска",
        summary="x",
        event_date=date(1762, 1, 1),
        importance=Entry.Importance.MAJOR,
    )


def test_model_clean_rejects_bad_payload(entry: Entry) -> None:
    question = Question(entry=entry, type="true_false", prompt="?", explanation="x", payload={})
    with pytest.raises(ValidationError):
        question.full_clean()


def test_form_builds_multiple_choice_payload(entry: Entry) -> None:
    form = QuestionForm(
        data={
            "type": "multiple_choice",
            "prompt": "Кой написва историята?",
            "choices": "Софроний\n* Паисий \n\nРаковски",
            "explanation": "Паисий Хилендарски.",
        },
        instance=Question(entry=entry),
    )
    assert form.is_valid(), form.errors
    question = form.save()
    assert question.payload == {"options": ["Софроний", "Паисий", "Раковски"], "correct": 1}


def test_form_round_trips_payload_into_fields(entry: Entry) -> None:
    question = Question.objects.create(
        entry=entry, type="true_false", prompt="?", explanation="x", payload={"answer": False}
    )
    assert QuestionForm(instance=question).initial["true_false_answer"] == "false"
    question.type, question.payload = "multiple_choice", {"options": ["А", "Б"], "correct": 1}
    assert QuestionForm(instance=question).initial["choices"] == "А\n*Б"


def test_form_reports_missing_correct_option(entry: Entry) -> None:
    form = QuestionForm(
        data={"type": "multiple_choice", "prompt": "?", "choices": "А\nБ", "explanation": "x"},
        instance=Question(entry=entry),
    )
    assert not form.is_valid()
    assert "Exactly one option must be marked correct." in form.non_field_errors()


# Admin


@pytest.fixture
def admin_client(db: None) -> Client:
    client = Client()
    client.force_login(User.objects.create_superuser("owner", "owner@example.com", "pw"))
    return client


def _entry_post(entry: Entry, status: str, questions: int) -> dict[str, Any]:
    data: dict[str, Any] = {
        "type": entry.type,
        "title": entry.title,
        "slug": entry.slug,
        "status": status,
        "summary": entry.summary,
        "event_date": entry.event_date,
        "date_certainty": "exact",
        "importance": entry.importance,
        "year_order": 0,
        **EMPTY_INLINES,
        "questions-TOTAL_FORMS": questions,
        "questions-INITIAL_FORMS": 0,
    }
    for i in range(questions):
        data |= {
            f"questions-{i}-type": "true_false",
            f"questions-{i}-prompt": f"Твърдение {i}",
            f"questions-{i}-true_false_answer": "true",
            f"questions-{i}-explanation": "x",
        }
    return data


def test_admin_blocks_publishing_with_five_questions(admin_client: Client, entry: Entry) -> None:
    url = f"/admin/content/entry/{entry.pk}/change/"
    response = admin_client.post(url, _entry_post(entry, "published", 5))
    assert response.status_code == 200
    assert "at least 6 questions" in response.content.decode()
    entry.refresh_from_db()
    assert entry.status == "draft"
    assert not Question.objects.filter(entry=entry).exists()


def test_admin_publishes_with_six_questions(admin_client: Client, entry: Entry) -> None:
    url = f"/admin/content/entry/{entry.pk}/change/"
    response = admin_client.post(url, _entry_post(entry, "published", 6))
    assert response.status_code == 302
    entry.refresh_from_db()
    assert entry.status == "published"
    assert Question.objects.filter(entry=entry).count() == 6


def test_admin_allows_draft_with_few_questions(admin_client: Client, entry: Entry) -> None:
    url = f"/admin/content/entry/{entry.pk}/change/"
    assert admin_client.post(url, _entry_post(entry, "draft", 2)).status_code == 302
    assert Question.objects.filter(entry=entry).count() == 2


def test_question_list_is_searchable(admin_client: Client, entry: Entry) -> None:
    Question.objects.create(
        entry=entry,
        type="true_false",
        prompt="Паисий е монах.",
        explanation="x",
        payload={"answer": True},
    )
    page = admin_client.get("/admin/quizzes/question/?q=монах").content.decode()
    assert "Паисий е монах." in page
    assert "1 question" in page
    assert admin_client.get("/admin/quizzes/question/add/").status_code == 403
