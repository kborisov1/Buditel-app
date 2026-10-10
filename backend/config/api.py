from ninja import NinjaAPI, Schema
from ninja.security import django_auth

from apps.accounts.api import router as auth_router
from apps.content.api import router as entries_router
from apps.gamification.api import router as dashboard_router
from apps.progress.api import router as review_router
from apps.quizzes.api import router as quiz_router

# Authenticated by default; public endpoints opt out with auth=None.
api = NinjaAPI(title="Buditel API", version="0.1.0", auth=django_auth)
api.add_router("/auth", auth_router)
api.add_router("", entries_router)
api.add_router("", quiz_router)
api.add_router("", dashboard_router)
api.add_router("", review_router)


class HealthOut(Schema):
    status: str


@api.get("/health", response=HealthOut, auth=None)
def health(request) -> HealthOut:  # type: ignore[no-untyped-def]
    return HealthOut(status="ok")
