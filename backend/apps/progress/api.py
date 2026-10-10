"""Review endpoints (architecture 4, 6.3). Every answer returns the explanation; the link
back to the entry comes only with a wrong answer (scope 5)."""

from datetime import date
from typing import Literal, cast

from django.contrib.auth.models import User
from django.http import HttpRequest
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.quizzes.api import Answer, QuestionOut, QuestionResultOut, SubmitIn
from apps.quizzes.grading import correct_answer
from apps.quizzes.quiz import shown_question

from . import older_check
from .models import OlderEventCheck
from .review import InvalidAnswer, NotDue, answer_review, review_queue
from .session import build_session

router = Router(tags=["session"])


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


# Daily session (scope 7.1)


class ReviewStepOut(Schema):
    kind: Literal["review"] = "review"
    count: int


class CheckStepOut(Schema):
    """An older-event check: open now when `check_id` is set, otherwise planned."""

    kind: Literal["check"] = "check"
    check_id: int | None


class EntryStepOut(Schema):
    kind: Literal["entry"] = "entry"
    slug: str
    title: str
    type: str
    progress: str | None


class SessionOut(Schema):
    steps: list[ReviewStepOut | CheckStepOut | EntryStepOut]


@router.get("/session", response=SessionOut)
def session(request: HttpRequest) -> SessionOut:
    steps: list[ReviewStepOut | CheckStepOut | EntryStepOut] = []
    for step in build_session(_user(request)):
        if step.kind == "review":
            steps.append(ReviewStepOut(count=step.count))
        elif step.kind == "check":
            steps.append(CheckStepOut(check_id=step.check_id))
        elif step.entry is not None:
            e = step.entry
            steps.append(
                EntryStepOut(slug=e.slug, title=e.title, type=e.type, progress=step.progress)
            )
    return SessionOut(steps=steps)


# Older-event check (scope 4.1)


class CheckOut(Schema):
    check_id: int
    questions: list[QuestionOut]


class CheckResultOut(Schema):
    score: int
    total: int
    xp_awarded: int
    results: list[QuestionResultOut]


def _open_check(request: HttpRequest, check_id: int) -> OlderEventCheck:
    try:
        return older_check.open_check(_user(request), check_id)
    except OlderEventCheck.DoesNotExist:
        raise HttpError(404, "Not found") from None
    except older_check.CheckClosed:
        raise HttpError(409, "Already submitted") from None


@router.get("/checks/{check_id}", response=CheckOut)
def get_check(request: HttpRequest, check_id: int) -> CheckOut:
    check = _open_check(request, check_id)
    items = check.items.select_related("question")
    return CheckOut(
        check_id=check.pk, questions=[QuestionOut(**shown_question(i.question)) for i in items]
    )


@router.post("/checks/{check_id}/submit", response=CheckResultOut)
def submit_check(request: HttpRequest, check_id: int, payload: SubmitIn) -> CheckResultOut:
    answers = {a.question_id: a.answer for a in payload.answers}
    if len(answers) != len(payload.answers):
        raise HttpError(400, "Each question can be answered once")
    try:
        result = older_check.submit_check(_user(request), check_id, answers)
    except OlderEventCheck.DoesNotExist:
        raise HttpError(404, "Not found") from None
    except older_check.CheckClosed:
        raise HttpError(409, "Already submitted") from None
    except older_check.InvalidAnswers as error:
        raise HttpError(400, str(error)) from None
    return CheckResultOut(
        score=result.check.score or 0,
        total=len(result.items),
        xp_awarded=result.check.xp_awarded,
        results=[
            QuestionResultOut(
                question_id=i.question_id,
                correct=bool(i.correct),
                your_answer=cast(Answer, i.answer),
                correct_answer=correct_answer(i.question.type, i.question.payload),
                explanation=i.question.explanation,
            )
            for i in result.items
        ],
    )
