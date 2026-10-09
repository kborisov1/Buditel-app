# Buditel-app

A gamified web app for learning the Bulgarian National Revival (1762–1878) through curated, chronological entries, quizzes, XP, daily streaks, and spaced review.

## Getting started

Prerequisites: Python 3.12, `uv`, Node LTS, Docker. See `docs/architecture.md` section 12.

```bash
cp .env.example .env   # then edit the values
make install
make db
make backend           # http://127.0.0.1:8000
make frontend          # http://127.0.0.1:5173
```

Other targets: `make test`, `make lint`, `make types`, `make backup`.
