"""Quiz endpoints (architecture 4, 6.2). A failed attempt returns the score only, so correct
answers are never sent before submission or after a fail."""

from typing import Literal, cast

from django.contrib.auth.models import User
from django.http import HttpRequest
from ninja import Query, Router, Schema
from ninja.errors import HttpError
from pydantic import Field

from apps.content.library import published_entries
from apps.progress.reading import EntryLocked

from . import practice
from .grading import correct_answer
from .models import Question, QuizAttempt
from .quiz import (
    AlreadySubmitted,
    InvalidAnswers,
    ReadingNotFinished,
    shown_question,
    start_quiz,
    submit_quiz,
)

router = Router(tags=["quiz"])

Answer = int | bool | list[str] | str


class QuestionOut(Schema):
    id: int
    type: str
    prompt: str
    options: list[str] | None = None
    items: list[str] | None = None


class QuizOut(Schema):
    attempt_id: int
    questions: list[QuestionOut]


class AnswerIn(Schema):
    question_id: int
    answer: Answer


class SubmitIn(Schema):
    answers: list[AnswerIn]


class QuizFailedOut(Schema):
    passed: Literal[False] = False
    score: int
    total: int


class QuestionResultOut(Schema):
    question_id: int
    correct: bool
    your_answer: Answer
    correct_answer: Answer
    explanation: str


class QuizPassedOut(Schema):
    passed: Literal[True] = True
    score: int
    total: int
    xp_awarded: int
    results: list[QuestionResultOut]


def _user(request: HttpRequest) -> User:
    return cast(User, request.user)


@router.post("/entries/{slug}/quiz", response=QuizOut)
def start(request: HttpRequest, slug: str) -> QuizOut:
    entry = published_entries().filter(slug=slug).first()
    if entry is None:
        raise HttpError(404, "Not found")
    try:
        attempt = start_quiz(_user(request), entry)
    except EntryLocked:
        raise HttpError(403, "Entry is locked") from None
    except ReadingNotFinished:
        raise HttpError(409, "Finish reading first") from None
    items = attempt.items.select_related("question")
    return QuizOut(
        attempt_id=attempt.pk,
        questions=[QuestionOut(**shown_question(i.question)) for i in items],
    )


@router.post("/quiz-attempts/{attempt_id}/submit", response=QuizPassedOut | QuizFailedOut)
def submit(
    request: HttpRequest, attempt_id: int, payload: SubmitIn
) -> QuizPassedOut | QuizFailedOut:
    answers = {a.question_id: a.answer for a in payload.answers}
    if len(answers) != len(payload.answers):
        raise HttpError(400, "Each question can be answered once")
    try:
        result = submit_quiz(_user(request), attempt_id, answers)
    except QuizAttempt.DoesNotExist:
        raise HttpError(404, "Not found") from None
    except AlreadySubmitted:
        raise HttpError(409, "Already submitted") from None
    except InvalidAnswers as error:
        raise HttpError(400, str(error)) from None
    attempt = result.attempt
    score = attempt.score or 0
    if not attempt.passed:
        return QuizFailedOut(score=score, total=result.total)
    return QuizPassedOut(
        score=score,
        total=result.total,
        xp_awarded=attempt.xp_awarded,
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


# Practice (scope 7.5)


class PracticeFilters(Schema):
    track: int | None = None
    phase: int | None = None
    count: int = Field(practice.DEFAULT_COUNT, ge=1, le=practice.MAX_COUNT)


class PracticeOut(Schema):
    questions: list[QuestionOut]


class PracticeAnswerIn(Schema):
    question_id: int
    answer: Answer


class PracticeResultOut(Schema):
    correct: bool
    correct_answer: Answer
    explanation: str
    xp_awarded: int


@router.get("/practice", response=PracticeOut)
def practice_set(request: HttpRequest, filters: Query[PracticeFilters]) -> PracticeOut:
    questions = practice.practice_questions(
        _user(request), track_id=filters.track, phase_id=filters.phase, count=filters.count
    )
    return PracticeOut(questions=[QuestionOut(**shown_question(q)) for q in questions])


@router.post("/practice/answer", response=PracticeResultOut)
def practice_answer(request: HttpRequest, payload: PracticeAnswerIn) -> PracticeResultOut:
    try:
        result = practice.answer_practice(_user(request), payload.question_id, payload.answer)
    except Question.DoesNotExist:
        raise HttpError(404, "Not found") from None
    except practice.NotPracticable:
        raise HttpError(403, "Only questions from read entries can be practiced") from None
    except practice.InvalidAnswer as error:
        raise HttpError(400, str(error)) from None
    question = result.question
    return PracticeResultOut(
        correct=result.correct,
        correct_answer=correct_answer(question.type, question.payload),
        explanation=question.explanation,
        xp_awarded=result.xp_awarded,
    )
