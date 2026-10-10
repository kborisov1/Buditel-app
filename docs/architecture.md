# Architecture: Bulgarian National Revival Learning App

Status: proposal, companion to `scope.md`. This file covers the technical design only. Product rules live in `scope.md`, and section numbers below (for example "scope 4") refer to it. Values marked *assumption* are choices made here where the scope is silent or ambiguous.

---

## 1. Decisions at a glance

| Area | Choice | Main reason |
|---|---|---|
| Backend | Python 3.12, Django, Django Ninja | Relational, rule-heavy domain; built-in admin covers most of scope 9 |
| Database | PostgreSQL 16 | Relational integrity, JSONB, trigram search, easy to scale |
| Frontend | React, TypeScript, Vite, Tailwind, D3 | Interactive SPA behind a login; D3 for the zoomable timeline |
| Auth | Django cookie sessions, Argon2, CSRF | Matches admin-managed accounts (scope 8); simpler and safer than JWT |
| Admin | Stock Django admin, extended | Single author, internal, English-only |
| Repo | Monorepo: `backend/`, `frontend/`, `docs/` | One commit can change API, UI and types together |
| Local run | Postgres in Docker; Django and Vite run natively | Fast reload, simple debugging |
| Hosting | Deferred; full containerization later | Packaging task, no redesign |

The load profile is database-bound (progress lookups, unlock computation, quiz grading), not CPU-bound. The performance work that matters is good indexing and avoiding N+1 queries, not language choice.

---

## 2. System overview

```
Browser (React SPA)
   |  JSON over HTTPS, session cookie
   v
Django (Gunicorn in prod, runserver in dev)
   |-- /api/*     Django Ninja: learner API (OpenAPI generated)
   |-- /admin/*   Django admin, extended
   |-- /media/*   uploaded images
   v
PostgreSQL
```

In development the Vite dev server proxies `/api`, `/admin` and `/media` to Django, so the browser sees one origin. This means no CORS configuration and the same cookie behavior as production.

---

## 3. Repository layout

```
repo/
  docs/            scope.md, architecture.md
  backend/
    manage.py
    config/        settings (base, dev, prod), urls
    apps/
      accounts/    user profile, timezone, date offset
      content/     entries, relations, sources, images, tracks, gates, phases
      quizzes/     questions, attempts, grading, daily challenge
      progress/    entry progress, unlock engine, review (SRS), older-event check
      gamification/ XP ledger, levels, streaks, daily goal
      activity/    activity log
      core/        clock service, settings model, shared helpers
    tests/
  frontend/
    src/
      api/         generated types and client
      features/    dashboard, timeline, library, entry, quiz, practice, profile
      components/
      i18n/        bg.json
  compose.yaml     Postgres for local dev
  Makefile
```

Business rules live in plain service modules inside each app (for example `progress/unlock.py`, `gamification/streaks.py`), not in views or models. This keeps them unit-testable without HTTP.

---

## 4. Backend

**Framework.** Django with Django Ninja. Ninja gives typed endpoints and an OpenAPI schema for free, which drives frontend type generation (section 7). Django REST Framework would also work; Ninja is lighter and less boilerplate for this API size.

**Auth.** Session cookies, `SessionAuthentication` plus CSRF on all unsafe methods. Passwords hashed with Argon2. There is no signup or self-service reset in v1 (scope 8): accounts are created and reset in the admin. One superuser is the owner; all others are plain users.

**Language and strings.** Code, admin, logs and API field names are English. All user-facing text is Bulgarian and lives in the frontend i18n files. Content (entry text, questions, explanations) is stored in Bulgarian as authored.

**API surface (v1, indicative).**

- `auth`: login, logout, current user
- `dashboard`: one aggregate call (goal, streak, due reviews, continue-reading, level)
- `timeline`: events with date, certainty, importance, phase, lock state
- `entries`: list with filters, detail, "finished reading"
- `quiz`: start attempt, submit attempt
- `review`: today's queue, answer
- `practice`: start a session from topic and period
- `daily-challenge`: get, answer
- `profile`: stats, per-track progress, result history
- `search`: title search

---

## 5. Data model

**Content tables** (authored through admin)

- `Entry`: type, slug, title, summary, `body_md`, event date, `date_certainty` (exact, approximate, estimated), `date_note_old_style`, region, importance (events only), `year_order` (explicit order within a year), status (draft, published).
- `EntryRelation`: structured links between entries. Relations are symmetric and untyped: each link is stored as a mirrored pair of rows (A to B and B to A), kept in sync by the model, so each entry's admin page and related sidebar list it. Grouping (people, places and so on) comes from the target's entry type. Only these relations count as "linked" for unlocking (scope 3.4). `[[entry-name]]` links in the body are resolved against slugs at serve time and never affect unlocking.
- `Source`: citations per entry.
- `Image`: file (validated with Pillow, width and height recorded), position (unique per entry), caption, credit, license note. Images form an ordered gallery, and the first one is the main image. The body can also place an image inline with `![[position]]`.
- `Phase`: name, start and end dates (timeline bands, may overlap). An event's phase is derived from its date, not stored.
- `Track`: name, kind (`regular`, `opening`, `finale`; at most one opening and one finale), position. `TrackEntry`: track, event, position (unique per track). An event can appear in several tracks. Only events can be in tracks or gates; an entry in a track or gate cannot change its type.
- `GateRequirement`: event, required event. An event with one or more requirements is a gate event: it unlocks only after all of them are read and passed. A separate `Gate` table is not needed.
- `Question`: entry FK, type (`multiple_choice`, `true_false`, `date_ordering`, `fill_blank`), prompt, `payload` JSONB, explanation. Payload shape depends on type and is validated with Pydantic models on save:
  - `multiple_choice`: `{"options": [2-6 unique strings], "correct": index}`, exactly one correct option.
  - `true_false`: `{"answer": bool}`, whether the prompt statement is true.
  - `date_ordering`: `{"items": [3-6 unique strings]}`, stored in the correct chronological order and shuffled when shown.
  - `fill_blank`: `{"answers": [1-10 accepted strings]}`. The prompt contains exactly one blank (`___`). Grading ignores case, extra whitespace and punctuation.
- `AppSetting`: key and JSON value rows for tunables (finale percentage, XP values, pass mark, level curve). Each known key has a default and a validator in `core/app_settings.py`; `get_setting(key)` returns the stored value or the default. New tunables are added there and seeded by a data migration.

**Per-user tables**

- `Profile`: user, time zone, `date_offset_days`, current streak, longest streak, freezes held, last active local date, completed-entries counter (for the older-event check).
- `EntryProgress`: user, entry, state (`in_progress`, `read`), finished-reading timestamp, passed timestamp. Absence of a row means no progress. Lock state is computed, never stored.
- `QuizAttempt` and `QuizAttemptQuestion`: the drawn question IDs, submitted answers, score, result.
- `QuestionState`: user, question, SRS box (0 to 4 mapping to 1, 3, 7, 14, 30 days), due date, miss count, last answered. Created on first miss (scope 5).
- `XpEvent`: append-only ledger (user, kind, amount, local date, reference). Total XP and level are derived by summing.
- `DailyChallenge`: user, local date, fixed question IDs, completion state.
- `ActivityLog`: user (nullable), timestamp, category (user, content, error), event type, JSONB details. Indexed on user, timestamp and type.

**Indexes to add from the start.** `EntryProgress(user, entry)` unique, `QuestionState(user, due_date)`, `XpEvent(user, local_date)`, `TrackEntry(track, position)`, a trigram index on `Entry.title`.

**Why a ledger for XP.** XP values and the level curve are explicitly "starting values" (scope header). With a ledger plus derived totals, retuning is a code or setting change, not a data migration.

---

## 6. Rules engine

All rules run on the server. The client only displays results.

### 6.1 Unlocking (scope 3)

- An **event** is unlocked when, for every track it belongs to, the previous event in that track is `read`, and all its gate requirements are `read`. For multi-track events, all tracks must allow it.
- The first event of every non-opening track additionally requires all events of the **opening** track (Awakening) to be `read`.
- A **non-event entry** is unlocked once any linked event is `read`.
- The **Finale** track's first event unlocks when, in every other track, the user has read at least `ceil(pct * event_count)` events, where `pct` comes from `AppSetting` (default 80%).
- An event in no track has no order constraint: it unlocks once its gate requirements are read, or immediately if it has none. The unlock graph view should flag such events.
- A read entry is always unlocked (scope 3.4), whatever the current track order and gates say.
- Only **published** entries take part. Drafts are never unlocked, and a draft event is skipped in track order, gate requirements, relations and the finale count, so an unpublished event never blocks learners.
- The engine lives in `progress/unlock.py`: a pure function over an in-memory graph and the user's set of read entry IDs, plus a loader that builds the graph from the database.
- With about 50 entries, the full unlock state for a user is computed per request from three small queries (progress, track order, gates). No cache is needed in v1. If it becomes slow, the cache key is the user's last progress timestamp.
- **Locked entry responses** contain only the fields allowed by scope 3.4 (title, plus date for timeline). The body is never serialized, so nothing leaks through the network tab. Separate serializers for locked and unlocked entries make this hard to get wrong.

### 6.2 Reading and quiz (scope 4)

1. "Finished reading" sets the progress row to `in_progress` with a timestamp and enables the quiz.
2. Starting a quiz requires "Finished reading" and an unlocked entry. It draws 5 questions from the entry's pool without replacement, giving questions the user has a `QuestionState` for the weight `quiz_missed_weight` (weighted random keys). The server stores the attempt with the chosen IDs.
3. The client sends all answers at once. The server grades, then stores the result.
4. On fail, the response contains only the score. On pass (`quiz_pass_percentage`, 4 of 5 by default), it contains explanations and correct answers, the entry becomes `read`, and XP is awarded. A first pass (the entry was not yet `read`) gives `xp_quiz_first_pass` and increments the older-event counter; later passes give `xp_quiz_retake`.
5. Correct answers are never sent before submission, and not at all on a failed attempt.
6. Wrong answers create or reset a `QuestionState` row.

### 6.3 Spaced repetition (scope 5)

Leitner-style boxes with fixed intervals 1, 3, 7, 14, 30 days. A correct answer moves up one box and sets the next due date; at the last box it stays there and comes back every 30 days. A wrong answer resets to box 0 (due in 1 day). The daily queue (`GET /api/review`) is `QuestionState` where `due_date <= today`, most overdue first, limited to entries the user can open (drafts and locked entries wait). Answers go one at a time (`POST /api/review/answer`) and only for questions in today's queue, so a question cannot be answered twice for XP on the same day. A correct answer awards `xp_review_correct` through the daily-goal rules (6.5). Review answers always return the explanation; the entry link is included only for wrong answers, and the correct answer itself is not sent.

### 6.4 Older-event check (scope 4.1)

The `Profile` completed-entries counter increments on each first pass. When it reaches a multiple of 3, the next session step is a check of 2 to 3 questions drawn from already-read entries. There is no pass mark, and 3 XP is awarded per correct answer.

### 6.5 XP, levels, daily goal (scope 6)

- XP values come from `AppSetting`. Every award writes an `XpEvent`.
- Level thresholds: level 1 to 2 needs 100 XP, each next level needs 25 more. The level is derived from total XP by a closed-form formula (arithmetic series), not a loop over a table. Titles are a lookup by level range.
- The daily goal is the sum of that day's `XpEvent` amounts for the user's local date, against 40. Reaching it writes a one-time 10 XP bonus event for that day. After the goal is reached, awards are multiplied by 0.8 and rounded.
- Login XP (5) is awarded on the first authenticated request of the local day, together with the streak update (6.6), and counts toward the goal.
- Goal, overflow rate and level curve come from `AppSetting` (`daily_goal_xp`, `goal_overflow_percentage`, `level_base_xp`, `level_step_xp`). Awards for one user are serialized on the profile row so the bonus is written once.
- The API returns titles as stable English keys (`peasant` to `apostle`); the Bulgarian names live in the frontend i18n file.
- `GET /api/dashboard` returns goal, streak, level and the count of due reviews. Continue-reading comes from the entries list.

### 6.6 Streaks and freezes (scope 6.3)

Evaluated lazily, with no scheduler, by `DailyActivityMiddleware` on the user's first `/api/` request of the local day (`gamification/streaks.py`). Given `last_active_local_date` and today's local date, the number of missed days is `today - last - 1`. If the freezes held cover all missed days, that many are consumed; otherwise the streak resets to 0 and the freezes are kept (scope 6.3). A streak day is recorded after the missed days are resolved. A freeze is granted at each multiple of 7 in the streak, capped at 2 held. Longest streak is updated on every increment.

### 6.7 Daily challenge and weak topics (scope 6.5, 6.6)

- Weak-topic score per entry combines the user's miss rate on that entry's questions with recency (recent misses weigh more). It is computed on demand from `QuizAttemptQuestion` and `QuestionState`, and aggregated to track level for display.
- The daily challenge is generated on the first request of the local day: about 10 questions, picked from the weakest entries among unlocked ones, then saved as a `DailyChallenge` row so it stays fixed for the day.
- The challenge is gated to unlocked entries only. If the user has too few weak topics, it fills from general unlocked questions.

### 6.7 Practice (scope 7.5)

Draws only from unlocked entries, filtered by topic and period. It awards 2 XP per correct answer and never creates a quiz attempt.

---

## 7. Time handling

A single `core.clock.now(user)` function is the only place the code reads the current time. It returns real UTC time plus the user's `date_offset_days`, converted to the user's time zone. Every rule above (streaks, due dates, daily goal, daily challenge) calls it. This makes the admin "shift date forward" tool (scope 9) a field edit, and makes tests deterministic by patching one function. Direct calls to `datetime.now()` or `timezone.now()` outside `core.clock` are banned by a lint rule.

The time zone is stored per user, with a default of the browser's zone captured at first login. The streak day rolls over at local midnight.

---

## 8. Frontend

**Stack.** React 18 with TypeScript, built with Vite. Routing with React Router. Server state with TanStack Query (caching, refetch after quiz or review). Tailwind CSS with design tokens for the parchment and mocha theme. Minimal global client state; the server is the source of truth.

**API types.** The backend publishes an OpenAPI schema. `openapi-typescript` generates types into `frontend/src/api/` (`make types`). A CI or pre-commit check fails if generated types are stale.

**Timeline.** D3 provides scales and zoom behavior only. React renders the SVG. Semantic zoom works as follows: the visible year range determines a minimum importance level, so zooming in reveals notable and minor events. Phase bands are rectangles on a separate layer and may overlap. Locked events render with title and date only. A click opens the side panel, which fetches the entry summary. The panel's quiz button is enabled only when the entry's progress is `in_progress` or later.

**Typography and theme.** Self-hosted fonts with full Cyrillic coverage: a serif for body text Source Serif 4 and a clean sans for UI. Theme tokens (parchment, cappuccino, mocha) are CSS variables defined once, so retuning colors is a single-file change. No animations or sounds in v1.

**i18n.** `react-i18next` from the start with a single `bg.json`. All UI strings go through it, so additional languages later only add files.

**Markdown rendering.** `react-markdown` with a small remark plugin for `[[entry-name]]` links, where `entry-name` is the target's slug. `[[slug|label]]` overrides the displayed text (useful for Bulgarian grammatical forms); otherwise the target's title is shown. The server returns the body with links resolved to entry IDs, and locked targets are rendered as plain titles. `![[position]]` places the entry's image with that position inline, with its caption and credit. Raw HTML in the body is not rendered. The same rendering code is bundled as a small script for the admin preview (`make admin-assets`, output git-ignored), so preview matches production. In the admin preview every slug resolves to the target's admin page, saved images are available by position, and unknown slugs or positions are highlighted.

---

## 9. Admin panel

The stock Django admin, extended. All admin text is English.

**Out of the box:** entries with inlines (sources, images, relations, questions), filters by type, status, region and track, searchable questions across entries, user creation and password reset, log browsing with filters by user, date and type.

**Custom pieces to build:**

- Markdown field with live preview, using the shared renderer.
- Publish guard: the entry page's question formset blocks `status=published` when the entry would have fewer than 6 questions (it sees questions added or deleted in the same save, which `Entry.clean()` cannot). Questions are added and deleted only on the entry page; the all-questions view is browse and edit only, so the guard cannot be bypassed.
- Question editing through plain per-type fields (options one per line with `*` marking the correct one, a true/false choice, items one per line, accepted answers one per line), converted to the JSON payload on save.
- Track and gate editing with ordering (drag-and-drop or a position field), plus the same-year `year_order`.
- **Unlock graph view:** a read-only page that builds the dependency graph from tracks and gates, draws it (D3 or Mermaid-style SVG), and flags unreachable entries (no path from any track start) and cycles. Optional for the first ~10 events, wanted as content grows.
- User tools: reset progress, shift date forward, as admin actions on the user page.
- Finale percentage and other tunables edited through the `AppSetting` model.

If a custom admin screen later outgrows Django admin templates, it can be replaced with a React screen on the same API and data model.

---

## 10. Activity logging

One `ActivityLog` table, written through a single `log_event(category, type, user, **details)` helper. Logged events: logins, quiz starts and results, XP awards, reviews, content edits (admin signal handlers), and server errors (a logging handler that writes exceptions to the table). Details go in JSONB. The admin list view filters by user, date range, category and type. Retention is unlimited in v1; add a pruning command if the table grows.

---

## 11. Search

Title search (scope 7) uses a Postgres `pg_trgm` index with `ILIKE` and similarity ranking on `Entry.title`, returning locked entries as title only. Full-text search through bodies is later (scope 11). Postgres ships no Bulgarian dictionary, so when that arrives the options are the `simple` configuration with trigram, or an external engine such as Meilisearch.

---

## 12. Local development (macOS)

**Prerequisites** (via Homebrew): Python 3.12, `uv` (dependency and virtualenv management), Node LTS, and Docker Desktop (OrbStack or Colima also work).

**Compose file** (`compose.yaml`, development only):

- One service `db`: `postgres:16`, named volume `pgdata`, port `5432` bound to `127.0.0.1`, credentials from a local `.env`.

**Daily commands** (wrapped in the `Makefile`):

| Command | Does |
|---|---|
| `make db` | `docker compose up -d db` |
| `make backend` | migrate, then `runserver` on `127.0.0.1:8000` |
| `make frontend` | Vite dev server on `127.0.0.1:5173`, proxying to Django |
| `make admin-assets` | build the admin Markdown preview bundle into Django static (also run by `make install`) |
| `make types` | regenerate frontend API types from the OpenAPI schema |
| `make test` | backend pytest, frontend unit tests |
| `make backup` | `pg_dump` to `backups/` with a timestamp, plus a copy of `media/` |
| `make seed` | load a small sample dataset (a few events, one track) for development |

Backups matter even locally, because the authored content is the project's main asset. `backups/` and `.env` are git-ignored. Content can additionally be exported to JSON fixtures (`dumpdata`) and committed, giving versioned history of what you write.

---

## 13. Testing

- **pytest** for the rules engine, which is where silent bugs would hurt: unlock graph (strict order, gates, multi-track, finale threshold, rounding up), SRS transitions, streak and freeze edge cases (two missed days, cap at 2, time zone rollover), XP ledger and level formula, and quiz draw and grading. These tests use the clock service so time is controlled.
- **API tests** confirm that locked entries never expose a body and that correct answers are absent from failed attempts.
- **Playwright** for a few end-to-end flows: log in, read, pass a quiz, see the next entry unlock, and see the streak update after a date shift.
- Formatting and linting: Ruff and mypy on the backend, ESLint and TypeScript strict mode on the frontend.

---

## 14. Deployment later (Stage 2)

Not needed now. When hosting becomes relevant, packaging is the only work:

- `backend/Dockerfile`, multi-stage: a Node stage builds the frontend, a Python stage installs dependencies and copies the built static files in, so the final image has no Node. Gunicorn serves Django and WhiteNoise serves static files.
- `compose.prod.yaml` adds three services: `db` (Postgres), `backend`, and `proxy` (Caddy for automatic HTTPS). Settings and secrets come from environment variables only.
- `media/` and `pgdata` stay on named volumes. Add scheduled `pg_dump` with off-server copies, and error tracking (for example Sentry) at that point.
- Production settings: `DEBUG=False`, secure cookies, HSTS, `ALLOWED_HOSTS`, and a real secret key. Because accounts are admin-managed, no email service is needed yet.

Claude Code can write and debug all of this when the time comes.

---

## 15. Scaling path

Nothing here needs a rewrite if usage grows beyond a small group.

1. Run several stateless Gunicorn instances behind the proxy. Sessions already live in the database, so no sticky routing is needed.
2. Move sessions to Redis if session reads become a hotspot.
3. Cache the computed unlock graph and weak-topic scores per user, invalidated on progress writes.
4. Add a read replica or connection pooling (PgBouncer) for Postgres.
5. Serve images and static files from object storage and a CDN.
6. Introduce a task queue (Celery or similar) only if background work appears, for example bulk question generation (scope, "later").

---

## 16. Alternatives considered

- **Full TypeScript (Next.js or NestJS with Prisma):** one language, but the admin panel would have to be built from scratch, costing weeks of non-learner work.
- **Supabase or Firebase:** fast auth and CRUD, but unlock, grading and streak logic would still need server functions, with vendor lock-in and a weaker back office.
- **JWT instead of sessions:** adds token handling and revocation problems for no benefit in a same-origin SPA.
- **Ready-made timeline library:** none supports overlapping bands plus importance-based reveal without heavy workarounds.
- **SQLite:** adequate at this size, but Postgres gives better search, JSON handling and a migration-free path to hosting.

---