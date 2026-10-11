from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db.models import QuerySet
from django.http import HttpRequest
from django.template.response import TemplateResponse

from .models import Profile
from .tools import MAX_SHIFT_DAYS, reset_progress, shift_date

CONFIRM_TEMPLATE = "admin/accounts/user/confirm_tool.html"


class ProfileInline(admin.StackedInline):  # type: ignore[type-arg]
    model = Profile
    can_delete = False


def _confirm(
    request: HttpRequest,
    users: QuerySet[User],
    action: str,
    message: str,
    submit: str,
    ask_days: bool = False,
) -> TemplateResponse:
    return TemplateResponse(
        request,
        CONFIRM_TEMPLATE,
        {
            "title": submit,
            "users": users,
            "action": action,
            "message": message,
            "submit": submit,
            "ask_days": ask_days,
            "max_days": MAX_SHIFT_DAYS,
        },
    )


class ProfileUserAdmin(UserAdmin):  # type: ignore[type-arg]
    inlines = [ProfileInline]
    actions = ["reset_progress_action", "shift_date_action"]

    @admin.action(description="Reset progress of selected users…")
    def reset_progress_action(
        self, request: HttpRequest, queryset: QuerySet[User]
    ) -> TemplateResponse | None:
        if request.POST.get("confirm") != "yes":
            return _confirm(
                request,
                queryset,
                "reset_progress_action",
                "This permanently removes reading progress, quiz attempts, reviews, checks, "
                "challenges, XP and streaks for these users. Accounts, time zones and date "
                "offsets stay.",
                "Reset progress",
            )
        for user in queryset:
            reset_progress(user, by=request.user)  # type: ignore[arg-type]
        self.message_user(request, f"Reset progress for {queryset.count()} user(s).")
        return None

    @admin.action(description="Shift date forward for selected users…")
    def shift_date_action(
        self, request: HttpRequest, queryset: QuerySet[User]
    ) -> TemplateResponse | None:
        if request.POST.get("confirm") != "yes":
            return _confirm(
                request,
                queryset,
                "shift_date_action",
                "Move these users' clocks forward to test streaks, reviews and daily goals. "
                "To undo, edit the date offset on the user page.",
                "Shift date",
                ask_days=True,
            )
        try:
            days = int(request.POST.get("days", ""))
            for user in queryset:
                shift_date(user, days, by=request.user)  # type: ignore[arg-type]
        except ValueError:
            self.message_user(
                request, f"Enter a whole number of days from 1 to {MAX_SHIFT_DAYS}.", messages.ERROR
            )
            return None
        self.message_user(request, f"Shifted {queryset.count()} user(s) forward by {days} day(s).")
        return None


admin.site.unregister(User)
admin.site.register(User, ProfileUserAdmin)
