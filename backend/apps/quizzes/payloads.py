"""Question payload shapes per type, validated with Pydantic (architecture 5)."""

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

BLANK = re.compile(r"_{3,}")


def _clean_list(values: list[str], what: str, low: int, high: int) -> list[str]:
    values = [v.strip() for v in values]
    if any(not v for v in values):
        raise ValueError(f"{what} cannot be empty.")
    if len({v.casefold() for v in values}) != len(values):
        raise ValueError(f"{what} must be unique.")
    if not low <= len(values) <= high:
        raise ValueError(f"Give between {low} and {high} {what.lower()}.")
    return values


class _Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MultipleChoice(_Payload):
    options: list[str]
    correct: int | None

    @field_validator("options")
    @classmethod
    def _options(cls, v: list[str]) -> list[str]:
        return _clean_list(v, "Options", 2, 6)

    @field_validator("correct")
    @classmethod
    def _correct(cls, v: int | None) -> int:
        if v is None:
            raise ValueError("Exactly one option must be marked correct.")
        return v

    @model_validator(mode="after")
    def _in_range(self) -> "MultipleChoice":
        if self.correct is not None and not 0 <= self.correct < len(self.options):
            raise ValueError("The correct option is out of range.")
        return self


class TrueFalse(_Payload):
    answer: bool | None

    @field_validator("answer")
    @classmethod
    def _answer(cls, v: bool | None) -> bool:
        if v is None:
            raise ValueError("Choose whether the statement is true or false.")
        return v


class DateOrdering(_Payload):
    # Listed in the correct chronological order; shuffled when shown.
    items: list[str]

    @field_validator("items")
    @classmethod
    def _items(cls, v: list[str]) -> list[str]:
        return _clean_list(v, "Items", 3, 6)


class FillBlank(_Payload):
    answers: list[str]

    @field_validator("answers")
    @classmethod
    def _answers(cls, v: list[str]) -> list[str]:
        return _clean_list(v, "Accepted answers", 1, 10)


SCHEMAS: dict[str, type[_Payload]] = {
    "multiple_choice": MultipleChoice,
    "true_false": TrueFalse,
    "date_ordering": DateOrdering,
    "fill_blank": FillBlank,
}


def question_errors(qtype: str, prompt: str, payload: Any) -> tuple[dict[str, Any], list[str]]:
    """Validate a question; return the normalized payload and a list of error messages."""
    errors: list[str] = []
    if qtype == "fill_blank" and len(BLANK.findall(prompt)) != 1:
        errors.append("A fill-in-the-blank prompt needs exactly one blank (___).")
    schema = SCHEMAS.get(qtype)
    if schema is None:
        return {}, [*errors, f"Unknown question type: {qtype}."]
    try:
        normalized = schema.model_validate(payload).model_dump()
    except ValidationError as exc:
        return {}, [*errors, *(str(e["msg"]).removeprefix("Value error, ") for e in exc.errors())]
    return normalized, errors
