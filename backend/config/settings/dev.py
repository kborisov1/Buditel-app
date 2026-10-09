from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = SECRET_KEY or "dev-only-insecure-key"  # noqa: F405
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
