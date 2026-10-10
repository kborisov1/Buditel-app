"""Review endpoints (architecture 4, 6.3). Every answer returns the explanation; the link
back to the entry comes only with a wrong answer (scope 5)."""

from datetime import date
from typing import cast

from django.contrib.auth.models import User
from django.http import HttpRequest
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.quizzes.api import Answer, QuestionOut
from apps.quizzes.quiz import shown_question

from .review import InvalidAnswer, NotDue, answer_review, review_queue

router = Router(tags=["review"])


class ReviewQueueOut(Schema):
    questions: list[QuestionOut]


class ReviewAnswerIn(Schema):
    question_id: int
    answer: Answer


class EntryLinkOut(Schema):
    slug: str
    title: str


class ReviewResultOut(Schema):
    correct: bool
    explanation: str
    xp_awarded: int
    next_due_date: date
    entry: EntryLinkOut | None


def _user(request: HttpRequest) -> User:
    return cast(User, request.user)


@router.get("/review", response=ReviewQueueOut)
def queue(request: HttpRequest) -> ReviewQueueOut:
    questions = review_queue(_user(request))
    return ReviewQueueOut(questions=[QuestionOut(**shown_question(q)) for q in questions])


@router.post("/review/answer", response=ReviewResultOut)
def answer(request: HttpRequest, payload: ReviewAnswerIn) -> ReviewResultOut:
    try:
        result = answer_review(_user(request), payload.question_id, payload.answer)
    except NotDue:
        raise HttpError(409, "Not due for review") from None
    except InvalidAnswer as error:
        raise HttpError(400, str(error)) from None
    entry = result.question.entry
    return ReviewResultOut(
        correct=result.correct,
        explanation=result.question.explanation,
        xp_awarded=result.xp_awarded,
        next_due_date=result.next_due,
        entry=None if result.correct else EntryLinkOut(slug=entry.slug, title=entry.title),
    )
