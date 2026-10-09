from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import CsrfViewMiddleware, get_token
from ninja import Router, Schema, Status
from ninja.errors import HttpError
from ninja.security import django_auth

from .validation import is_valid_time_zone

router = Router(tags=["auth"])


class LoginIn(Schema):
    email: str
    password: str
    time_zone: str | None = None


class UserOut(Schema):
    id: int
    email: str
    time_zone: str
    is_admin: bool


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.pk,
        email=user.email,
        time_zone=user.profile.time_zone,  # type: ignore[attr-defined]
        is_admin=user.is_superuser,
    )


def _enforce_csrf(request: HttpRequest) -> None:
    """Ninja views are CSRF-exempt; run Django's check for unauthenticated unsafe calls."""
    middleware = CsrfViewMiddleware(lambda r: HttpResponse())
    if middleware.process_view(request, lambda r: HttpResponse(), (), {}) is not None:
        raise HttpError(403, "CSRF check failed")


@router.get("/csrf", auth=None, response={204: None})
def csrf(request: HttpRequest) -> Status[None]:
    get_token(request)  # marks the CSRF cookie to be set on this response
    return Status(204, None)


@router.post("/login", auth=None, response=UserOut)
def login_view(request: HttpRequest, payload: LoginIn) -> UserOut:
    _enforce_csrf(request)
    match = User.objects.filter(email__iexact=payload.email.strip()).first()
    # Same error for unknown email and wrong password.
    user = None
    if match:
        user = authenticate(request, username=match.username, password=payload.password)
    if user is None or not user.is_active:
        raise HttpError(401, "Invalid credentials")
    first_login = user.last_login is None
    login(request, user)
    if first_login and payload.time_zone and is_valid_time_zone(payload.time_zone):
        user.profile.time_zone = payload.time_zone  # type: ignore[attr-defined]
        user.profile.save(update_fields=["time_zone"])  # type: ignore[attr-defined]
    return _user_out(user)


@router.post("/logout", auth=django_auth, response={204: None})
def logout_view(request: HttpRequest) -> Status[None]:
    logout(request)
    return Status(204, None)


@router.get("/me", auth=django_auth, response=UserOut)
def me(request: HttpRequest) -> UserOut:
    return _user_out(request.user)  # type: ignore[arg-type]
