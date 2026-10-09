from django.contrib import admin
from django.http import HttpRequest
from django.urls import reverse
from django.utils.html import format_html

from .forms import QuestionForm, QuestionInlineFormSet
from .models import Question

ANSWER_FIELDS = ["choices", "true_false_answer", "ordered_items", "accepted_answers"]


class QuestionInline(admin.StackedInline):  # type: ignore[type-arg]
    """Questions are written inside their entry's edit page (scope 2.4)."""

    model = Question
    form = QuestionForm
    formset = QuestionInlineFormSet
    extra = 1
    fields = ["type", "prompt", *ANSWER_FIELDS, "explanation"]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Searchable view of all questions. Adding and deleting happen on the entry page,
    where the publish guard applies."""

    form = QuestionForm
    list_display = ["prompt", "type", "entry_link"]
    list_filter = ["type", "entry__type", "entry__status"]
    search_fields = ["prompt", "explanation", "entry__title"]
    list_select_related = ["entry"]
    readonly_fields = ["entry_link"]
    fields = ["entry_link", "type", "prompt", *ANSWER_FIELDS, "explanation"]

    @admin.display(description="entry", ordering="entry__title")
    def entry_link(self, obj: Question) -> str:
        url = reverse("admin:content_entry_change", args=[obj.entry_id])
        return format_html('<a href="{}">{}</a>', url, obj.entry.title)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Question | None = None) -> bool:
        return False
