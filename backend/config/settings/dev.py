from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = SECRET_KEY or "dev-only-insecure-key"  # noqa: F405
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# The browser talks to the Vite dev server, which proxies to Django (architecture 2).
CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1:5173", "http://localhost:5173"]
