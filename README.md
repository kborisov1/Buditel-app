# Buditel-app

> **Status: abandoned.** Development on this project has stopped and will not resume. It was dropped because of planning misses and a tech stack that did not work out for the project. The repository stays public as a record of the scope, the design decisions, and the code written so far. It is not maintained, and no issues or pull requests are being reviewed.

A gamified web app for learning the Bulgarian National Revival (1762–1878) through curated, chronological entries, quizzes, XP, daily streaks, and spaced review.

## What is in this repository

- `docs/scope.md`: product rules, the v1 feature list (section 11), and what was planned for later phases.
- `docs/architecture.md`: the technical design, the data model, the rules engine, and the alternatives that were considered (section 16). Its status line still reads "proposal"; it was never updated after the project was dropped.
- `backend/`: Django and Django Ninja API, with apps for accounts, content, quizzes, progress, gamification, activity logging, and core. Tests live in `backend/tests/`.
- `frontend/`: React, TypeScript, and Vite single-page app, with its own tests.
- `docs/` and the git history show how the work was planned and how it changed over time.

The project was not finished. Check `docs/scope.md` section 11 against the code before you assume a feature exists.

## Test status when development stopped

- `make test`: 304 backend tests and 26 frontend tests pass.
- `make lint`: ruff, mypy, ESLint, and the TypeScript check pass.

## Why it was abandoned

- **Planning misses:** the initial planning did not hold up once the work started.
- **Tech stack:** the chosen tech stack was not suitable for the project.

Anyone who wants to reuse the content, the scope, or the design ideas is free to do so. Please do not treat the code as a maintained base.

## Getting started

These steps are kept so the project can still be run locally for review. They are not supported.

Prerequisites: Python 3.12, `uv`, Node LTS, Docker. See `docs/architecture.md` section 12.

```bash
cp .env.example .env   # then edit the values
make install
make db
make backend           # http://127.0.0.1:8000
make frontend          # http://127.0.0.1:5173
```

Other targets: `make test`, `make lint`, `make types`, `make backup`.

## Accounts

There is no signup (scope 8). Create the owner with `cd backend && uv run python manage.py createsuperuser`, then add learner accounts in `/admin/`. Learners log in with their **email**, so set it on every account and keep it unique.
