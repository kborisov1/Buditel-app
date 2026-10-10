"""Answer checking per question type (architecture 5, 6.2)."""

import unicodedata
from typing import Any

from .models import Question


def normalize_blank(text: str) -> str:
    """Fill-in-the-blank grading ignores case, extra whitespace and punctuation."""
    kept = "".join(c for c in text if not unicodedata.category(c).startswith("P"))
    return " ".join(kept.casefold().split())


def answer_error(question_type: str, answer: Any) -> str | None:
    """Why an answer has the wrong shape for its question type, or None."""
    match question_type:
        case Question.Type.MULTIPLE_CHOICE:
            valid, what = type(answer) is int, "an option index"
        case Question.Type.TRUE_FALSE:
            valid, what = type(answer) is bool, "true or false"
        case Question.Type.DATE_ORDERING:
            valid = isinstance(answer, list) and all(isinstance(i, str) for i in answer)
            what = "a list of items"
        case Question.Type.FILL_BLANK:
            valid, what = isinstance(answer, str), "a text answer"
        case _:
            raise ValueError(f"Unknown question type: {question_type}")
    return None if valid else f"Expected {what}."


def answer_set_error(questions: list[Question], answers: dict[int, Any]) -> str | None:
    """Why a full set of answers is unusable: every question once, each in the right shape."""
    if set(answers) != {q.pk for q in questions}:
        return "Answer every question, and only those."
    for question in questions:
        error = answer_error(question.type, answers[question.pk])
        if error:
            return f"Question {question.pk}: {error}"
    return None


def is_correct(question_type: str, payload: dict[str, Any], answer: Any) -> bool:
    match question_type:
        case Question.Type.MULTIPLE_CHOICE:
            return bool(answer == payload["correct"])
        case Question.Type.TRUE_FALSE:
            return bool(answer is payload["answer"])
        case Question.Type.DATE_ORDERING:
            return bool(answer == payload["items"])
        case Question.Type.FILL_BLANK:
            accepted = {normalize_blank(a) for a in payload["answers"]}
            return normalize_blank(answer) in accepted
    raise ValueError(f"Unknown question type: {question_type}")


def correct_answer(question_type: str, payload: dict[str, Any]) -> Any:
    """What to reveal after a passed quiz."""
    match question_type:
        case Question.Type.MULTIPLE_CHOICE:
            return payload["correct"]
        case Question.Type.TRUE_FALSE:
            return payload["answer"]
        case Question.Type.DATE_ORDERING:
            return payload["items"]
        case Question.Type.FILL_BLANK:
            return payload["answers"][0]
    raise ValueError(f"Unknown question type: {question_type}")
