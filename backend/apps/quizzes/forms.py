from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from apps.content.models import Entry
from apps.content.rules import publish_error

from .models import Question

Type = Question.Type


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


class QuestionForm(forms.ModelForm):  # type: ignore[type-arg]
    """Edits the JSON payload through plain per-type fields (architecture 9)."""

    choices = forms.CharField(
        label="Options",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Multiple choice: one option per line. Prefix the correct one with *.",
    )
    true_false_answer = forms.ChoiceField(
        label="Answer",
        required=False,
        choices=[("", "---------"), ("true", "True"), ("false", "False")],
        help_text="True/false: whether the prompt statement is true.",
    )
    ordered_items = forms.CharField(
        label="Items",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Date ordering: one item per line, in the correct chronological order.",
    )
    accepted_answers = forms.CharField(
        label="Accepted answers",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Fill in the blank: one per line. Mark the blank in the prompt with ___.",
    )

    class Meta:
        model = Question
        fields = ["type", "prompt", "explanation"]
        widgets = {
            "prompt": forms.Textarea(attrs={"rows": 2}),
            "explanation": forms.Textarea(attrs={"rows": 2}),
        }

    class Media:
        js = ["quizzes/admin/question-fields.js"]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        payload = self.instance.payload or {}
        match self.instance.type:
            case Type.MULTIPLE_CHOICE:
                self.initial["choices"] = "\n".join(
                    ("*" if i == payload.get("correct") else "") + option
                    for i, option in enumerate(payload.get("options", []))
                )
            case Type.TRUE_FALSE:
                answer = payload.get("answer")
                self.initial["true_false_answer"] = "" if answer is None else str(answer).lower()
            case Type.DATE_ORDERING:
                self.initial["ordered_items"] = "\n".join(payload.get("items", []))
            case Type.FILL_BLANK:
                self.initial["accepted_answers"] = "\n".join(payload.get("answers", []))

    def clean(self) -> dict[str, Any]:
        data = super().clean() or {}
        self.instance.payload = self._payload(data)
        return data

    def _payload(self, data: dict[str, Any]) -> dict[str, Any]:
        match data.get("type"):
            case Type.MULTIPLE_CHOICE:
                lines = _lines(data.get("choices", ""))
                marked = [i for i, line in enumerate(lines) if line.startswith("*")]
                return {
                    "options": [line.lstrip("*").strip() for line in lines],
                    "correct": marked[0] if len(marked) == 1 else None,
                }
            case Type.TRUE_FALSE:
                answer = data.get("true_false_answer")
                return {"answer": {"true": True, "false": False}.get(answer or "")}
            case Type.DATE_ORDERING:
                return {"items": _lines(data.get("ordered_items", ""))}
            case Type.FILL_BLANK:
                return {"answers": _lines(data.get("accepted_answers", ""))}
        return {}


class QuestionInlineFormSet(BaseInlineFormSet):  # type: ignore[type-arg]
    """Blocks publishing an entry with too few questions (scope 2.4)."""

    def clean(self) -> None:
        super().clean()
        count = sum(
            1 for form in self.forms if form.cleaned_data and not form.cleaned_data.get("DELETE")
        )
        error = publish_error(
            publishing=self.instance.status == Entry.Status.PUBLISHED, question_count=count
        )
        if error:
            raise ValidationError(error)
