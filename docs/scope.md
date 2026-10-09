# Project Scope: Bulgarian National Revival Learning App

Status: planning (product scope only). Tech stack and architecture are intentionally excluded and will be defined separately in `architecture.md`.

All previously open questions have been resolved (see section 12). Items marked **[LATER]** are deliberately out of v1. Numeric values (XP, levels, thresholds) are v1 starting values and are expected to be tuned during testing.

---

## 1. Vision

A gamified web app for learning and exploring the Bulgarian National Revival (Възраждане), **1762-1878**. Users read curated entries in chronological order, pass a short quiz after each one, earn XP, keep a daily streak, and review what they got wrong on a spaced schedule. The content is written and maintained by a single author (the project owner) through an admin panel.

- Platform: **desktop web only** for now.
- Period covered: 1762 (Paisius's history) to 1878 (Congress of Berlin). Nothing outside this period.
- User-facing language: **Bulgarian**. Backend, admin panel, code, and logs: **English**.
- Tone of content: a mix of academic precision and storytelling.
- Audience: not fixed to one group. During development, access is limited to the owner and a few test accounts.

---

## 2. Content Model

### 2.1 Entry types (all six in v1)
1. **Event** (the backbone, appears on the timeline)
2. **Person**
3. **Place**
4. **Institution** (schools, chitalishta, press, committees)
5. **Work** (documents, books, e.g. "История славянобългарска")
6. **Concept** (e.g. the church struggle)

Other types may be added later.

### 2.2 Entry structure
- Title, type, short summary, full body text (Markdown).
- Date with certainty flag (see 2.3), region, theme/track membership, importance level (events only).
- Links to other entries via `[[entry-name]]` syntax in the body, plus structured relations.
- Images (portraits, historical documents; sourced from public domain or the owner's own material).
- Sources/citations per entry (users can see where facts came from).
- Length is flexible: short summary card that expands into a full article.
- Status: draft / published, with preview before publishing.

### 2.3 Dates
- Only **New Style (Gregorian)** is stored.
- Optional free-text note for the Old Style date.
- Certainty flag: exact / approximate / estimated. It controls how the timeline displays the date.
- Entries without an exact date are placed at the best-guess date.
- Events in the same year have an explicit order set by the author in the admin panel.

### 2.4 Questions
- Each question belongs to exactly one entry. Written inside that entry's edit page.
- Admin also has a searchable "all questions" view for browsing and editing across entries.
- **Minimum 6 questions per entry** (admin blocks publishing below this).
- Question types in v1: **multiple choice, true/false, date ordering, fill-in-the-blank**. **[LATER]**: matching people to events, map-based questions.
- In v1 all questions are written manually by the author. Auto-generating questions from structured entry data (e.g. birth years) is **[LATER]**, after the first ~50 entries exist and the data is consistent.
- Every question has an explanation, shown only under the rules in section 5.
- No difficulty levels for now. **[LATER]**

### 2.5 Launch content
- Initial development content: **~10 events** (to start testing quickly), plus linked non-event entries.
- v1 content target: **~50 entries**.
- All content is written by the owner. No existing source dataset to import.
- Glossary of old terms and "Did you know" boxes: **[LATER]**.

---

## 3. Tracks, Phases, and Unlocking

### 3.1 Phases (timeline bands, based on dates)
Bands may overlap on the timeline.
1. Awakening, 1762 to about 1820
2. Education and early culture, about 1820 to 1856
3. Church struggle, about 1840 to 1870
4. National liberation struggle, about 1860 to 1876
5. Liberation, 1877 to 1878

### 3.2 Tracks (themes, based on unlocking)
Tracks run in parallel. Within each track, events unlock **strictly in order**.
- Awakening (short opening track every user starts with)
- Education and culture
- Church struggle
- Liberation struggle
- **Finale**: covers the 1877-1878 events and unlocks after the user has completed enough of every track.

Tracks are mostly aligned with phases but not identical. An event's **date** decides its phase band on the timeline. Its **track** decides when it unlocks. An event can belong to **several tracks**.

### 3.3 Gate events
The author can define gate events in the admin panel: an event that unlocks only after specified other events (possibly across tracks) are read and passed. Example: the April Uprising depends on progress in more than one track.

### 3.4 Unlock rules
- Event order is strict inside a track.
- Non-event entries (people, places, institutions, works, concepts) **unlock automatically when a linked event is read**. "Linked" means a structured relation set by the author; a `[[entry-name]]` mention in the body does not count.
- Locked entries stay visible in lists and on the timeline with minimal information:
  - Timeline: title and date.
  - Lists: title only.
  - Related sidebar: title only.
- Locked entries cannot be read.
- Admin tool to visualize the unlock graph to catch unreachable or stuck entries. Wanted once content grows. For the initial ~10 events it is optional.
- **Finale threshold:** the Finale unlocks when the user has read at least **80% of the events in every track**, rounded up. The percentage is an admin setting so it can be tuned as content grows.

---

## 4. Reading and Quiz Flow

1. User opens an unlocked entry and reads it.
2. User clicks a **"Finished reading"** button. This is the gate to the quiz, not scrolling or time spent.
3. A quiz is drawn randomly from the entry's question pool: **always exactly 5 questions** (the minimum pool of 6 guarantees this). Questions the user previously missed are favored.
4. All questions are answered first, then graded at the end.
5. **Pass mark: 80%**, which means **4 of 5** correct.
6. The quiz must be passed to mark the entry as **read** (this is what unlocks the next entries and counts for progress).
7. The user may leave and come back. The entry stays **"in progress"**.
8. **On fail:** only the score is shown. No correct answers are revealed. The user is told to re-read, then can retry.
9. **On pass:** explanations are shown for the questions.
10. Retakes are always possible but give much less XP (example: 50 XP first pass, 5 XP on retake).

### 4.1 Older-event check
- A separate short check of **2 to 3 questions** from older, already-read events.
- Appears **after every third entry** the user completes.
- Not part of the post-reading quiz.
- Has **no pass mark**. It gives XP per correct answer (see 6.1).

---

## 5. Review (Spaced Repetition)

- Missed questions return on a schedule of **1, 3, 7, 14, 30 days**. Each correct answer moves the question to the next interval. A wrong answer resets it to the start.
- Review is **mixed into the daily flow**, not a standalone required section (a "Review only" shortcut exists, see 7).
- Review sessions count toward the daily goal and give XP, at a lower rate than first-time quizzes.
- **Explanation** is shown after **every** review answer, right or wrong. The **link back to the entry** is shown only after a wrong answer.

---

## 6. XP, Levels, Streaks, Goals

### 6.1 XP
- XP is weighted by activity type. Starting values:
  - First-time post-reading quiz pass: **50 XP** (flat, not score-scaled).
  - Quiz retake: **5 XP**.
  - Correct answer in review or practice: **2 XP**.
  - Correct answer in an older-event check: **3 XP**.
  - Daily login: **5 XP**.
  - Daily goal completion bonus: **10 XP**.
- After the daily goal is reached, users can keep earning XP at a **20% reduced rate**.
- XP only for v1. A second currency (coins or similar) is **[LATER]**.

### 6.2 Levels and titles
- Level 1 to 2 needs **100 XP**. Each following level needs **25 XP more** than the previous one (level 2 to 3 needs 125, level 3 to 4 needs 150, and so on).
- A **title** is shown, and it changes every few levels rather than every level. Starting set (Bulgarian, user-facing):
  - Levels 1-2: Селянин
  - Levels 3-5: Ученик
  - Levels 6-8: Даскал
  - Levels 9-11: Читалищен деятел
  - Levels 12-14: Хайдутин
  - Levels 15-17: Комита
  - Levels 18-20: Войвода
  - Level 21 and above: Апостол
- **No animations** on level-up for v1.

### 6.3 Streaks
- A streak day counts on **any login**.
- The "day" rolls over at **midnight in the user's own time zone**.
- **Streak freeze**: earned once per 7-day streak, **max 2 held** at a time, applied **automatically** when a day is missed.
- A missed day uses a freeze automatically if one is held. Two missed days in a row use two freezes. With no freeze available, the streak resets to 0.
- A freeze is earned at every 7-day streak mark, up to the maximum of 2 held.
- The profile also stores the **longest streak**.

### 6.4 Daily goal
- Fixed for all users in v1 (not user-configurable). Target: **40 XP per day**, designed for about 10 minutes of activity. Passing one entry's quiz (50 XP) completes it on its own. A review-only day needs roughly 18 correct review answers together with the daily login bonus. Login XP counts toward the goal.
- Reaching it gives visual completion plus a small XP bonus.
- Must be reachable even when the user has no new content left (reviews, older-event checks, and practice count), so streaks never depend on how much content exists.

### 6.5 Daily challenge
- In v1. A **fixed set** of about 10 questions, selected automatically from the user's **weak topics**, with a completion bonus. It only selects existing hand-written questions, so no question generation is needed. A fixed set has a clear end, is easy to explain, and works with the daily goal.

### 6.6 Weak topics
- Measured **per entry**, from the user's question-level accuracy (how often questions from that entry are missed and how recently).
- Rolled up to **per-track** for display and for choosing the daily challenge.
- Optional theme tags added by the author **[LATER]**.

---

## 7. Screens and Navigation

Main menu: **Dashboard, Timeline, Library, Practice, Profile.**

Top bar: a simple **title search** covering unlocked entries and the titles of locked ones. Full-text search through entry bodies is **[LATER]**.

### 7.1 Dashboard (home after login)
A few "at a glance" panels:
- Daily goal progress
- Streak and freeze status
- Continue where you left off
- Reviews due today
- Level progress

Primary action: one **"Start today's session"** button that builds a queue: due reviews first, then the next entry on the user's tracks, with the older-event check inserted after every third entry. Secondary shortcuts: **Review only, Continue reading, Practice.**

### 7.2 Timeline
- One continuous horizontal line from 1762 to 1878, navigated by **zooming in and out** (not horizontal scrolling).
- **Events only** are shown.
- Events have 3 importance levels (**major, notable, minor**), set by the author. Zooming in reveals more events by importance level.
- Colored phase bands (see 3.1), which may overlap.
- Locked events appear with title and date only.
- **Clicking an event opens a side panel** that keeps the timeline visible. Panel contents: title, dates, places, people, short summary, and a big button to open the detailed entry page, plus a button to take the quiz (the quiz button becomes available only once "Finished reading" has been clicked on that entry). Locked events show only title and date in the panel.

### 7.3 Library
- Lists of people, events, places, institutions, works, and concepts.
- Filterable by theme, period, and region, and searchable by name.
- Locked entries appear as title only.

### 7.4 Entry page
- Markdown body, images, sources, "Finished reading" button.
- **Related entries sidebar** (title only for locked ones) and inline `[[entry-name]]` links.

### 7.5 Practice
- User picks a topic and period and practices questions. Draws **only from unlocked entries**.
- Gives XP at a low rate. Relaxed, non-competitive in v1.

### 7.6 Profile
- v1: level and title, streak, XP, per-track progress, history of results.
- **[LATER]**: list of read entries, weak-topics overview, per-topic mastery.

---

## 8. Accounts

- Email and password during development. Google SSO **[LATER]**.
- No guest mode in v1. Browsing requires an account.
- Access limited to a small group during development. At the moment it is the owner plus a few test accounts.
- Accounts are created and reset by the admin from the admin panel. No self-service password reset or email verification in v1.
- Multiple user accounts, plus one admin (the owner).

---

## 9. Admin Panel

- Create, edit, preview, and publish entries in **Markdown with live preview** and structured fields (type, date, certainty, region, theme, track membership, importance, links, sources, images). Draft/published status.
- Block publishing an entry with fewer than 6 questions.
- Write questions inside each entry. Searchable "all questions" view.
- Define track membership, order within tracks and within the same year, and gate events.
- Create and reset test accounts. Reset a user's progress. **Shift a user's date forward** to test streaks and review schedules.
- **Activity logging**, searchable and filterable by user, date, and event type. Covers user activity (logins, quizzes, XP), content changes, and errors.
- Unlock graph visual (see 3.4).
- Setting for the Finale unlock percentage.

---

## 10. Design Direction

- Mix of slightly modern UI (clean buttons) and period feeling.
- Easy-to-read font with **full Cyrillic support**.
- Parchment tones and light brownish / cappuccino / mocha as the main theme colors.
- Minimal feedback for v1 (no celebration animations or sounds). Playful feedback is **[LATER]**.
- App name: Buditel

---

## 11. v1 Scope Summary (Option B)

**In v1:**
- Accounts (email and password), admin-managed, group access
- Admin panel with Markdown editor, entries of all six types, questions, tracks, gates, test tools, searchable logs
- Zoomable timeline with importance levels and phase bands, side panel
- Library lists with filters and search
- Entry pages with links, images, sources, related sidebar
- Read tracking with mandatory post-reading quiz (80% pass, random draw up to 5)
- Parallel tracks with strict order, gate events, finale, locked-entry previews
- XP, levels with titles, per-track progress
- Login streak with automatic freezes, fixed daily goal with small bonus
- Spaced-repetition review mixed into the daily flow, older-event checks every third entry
- Practice area, explanations on wrong answers, link back to the entry
- Basic profile and home dashboard

**Later phases:**
- Interactive map and map-based questions
- Leaderboards, friends, competitive and timed modes
- Badges, coins, cosmetics
- Google SSO, password reset, email verification
- Glossary and "Did you know" boxes
- Difficulty levels, level-up animations, sounds
- Per-topic mastery, weak-topics overview, read entries on profile
- Full-text search through entry bodies
- Auto-generated questions from structured entry data
- Reset option for major edits to published entries
- Mobile support
- Additional languages

---