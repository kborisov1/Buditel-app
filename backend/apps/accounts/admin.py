from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Profile


class ProfileInline(admin.StackedInline):  # type: ignore[type-arg]
    model = Profile
    can_delete = False


class ProfileUserAdmin(UserAdmin):  # type: ignore[type-arg]
    inlines = [ProfileInline]


admin.site.unregister(User)
admin.site.register(User, ProfileUserAdmin)
