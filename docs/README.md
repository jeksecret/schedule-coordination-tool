# README — Database Schema (P1–P5)

This document explains the database schema powering the scheduling tool across:

- P1: Dashboard (session list & filters)

- P2: Session Create (Notion import → seed data)

- P3: Status & edits (admin view)

- P4: Evaluator Answer Form (token link)

- P5: Client/Facility Answer Form (token link)

Progress rule: answered / total is derived from session_evaluators.answered_at. An evaluator is “answered” once they submit the P4 form (even if they selected nothing, which is allowed by spec).

## High-level Model

facilities: A facility (imported from Notion).

sessions: One scheduling run for a facility (purpose, status, deadlines).

evaluators: People who respond to availability.

session_evaluators: Which evaluators belong to a session (+ tokens, answered_at).

candidate_slots: Candidate dates (and part of day).

evaluator_answers: Per-evaluator per-slot answer (O/○, M/△, X/×).

client_response: Facility’s final choice of a single slot (token link).

session_list_v: Read-only view for P1: list grid with progress & confirmed date.

See the ER diagram in schema.md.

## Enums

- purpose_enum: 訪問調査, 聞き取り, 場面観察, FB, その他

- status_enum: 起案中, 評価者待ち, 事業所待ち, 確定

## Tables

1) facilities (P2, P3, P5; P1 via view)

| Column                    | Type                 | Notes                                    |
| ------------------------- | -------------------- | ---------------------------------------- |
| id                        | `int` (identity, PK) | Internal ID                              |
| notion\_page\_id          | `text` (unique)      | Normalized Notion page ID (36-UUID form) |
| notion\_url               | `text`               | Original Notion link                     |
| name                      | `text`               | Facility name                            |
| contact\_name             | `text`               | Contact person name                      |
| contact\_email            | `text`               | Contact person email                     |
| last\_notion\_sync\_at    | `timestamptz`        | When Notion was last fetched             |
| created\_at / updated\_at | `timestamptz`        | `updated_at` is auto-stamped by trigger  |

- Why keep Notion linkage?
We import facility info by Notion URL and want a stable dedupe key (notion_page_id).

2) sessions (P1, P2, P3, P4, P5)

| Column                    | Type                       | Notes                              |
| ------------------------- | -------------------------- | ---------------------------------- |
| id                        | `int` (identity, PK)       | Shown on P1 grid                   |
| facility\_id              | `int` (FK → facilities.id) | Parent facility                    |
| purpose                   | `purpose_enum`             | e.g., 訪問調査                         |
| status                    | `status_enum`              | `起案中` → `評価者待ち` → `事業所待ち` → `確定`   |
| response\_deadline        | `date`                     | Evaluator response deadline        |
| presentation\_date        | `date`                     | Target date to present to facility |
| notion\_url               | `text`                     | Convenience link to Notion         |
| created\_at / updated\_at | `timestamptz`              | `updated_at` auto-stamped          |

3) evaluators (P2 upsert, P3 display, P4 submit)

| Column                    | Type                 | Notes                     |
| ------------------------- | -------------------- | ------------------------- |
| id                        | `int` (identity, PK) | —                         |
| name                      | `text`               | —                         |
| email                     | `text` (unique)      | Dedup key across sessions |
| created\_at / updated\_at | `timestamptz`        | —                         |

4) session_evaluators (P2 seed, P3 edit, P4 token + answered_at)

| Column                    | Type                       | Notes                                 |
| ------------------------- | -------------------------- | ------------------------------------- |
| id                        | `int` (identity, PK)       | —                                     |
| session\_id               | `int` (FK → sessions.id)   | —                                     |
| evaluator\_id             | `int` (FK → evaluators.id) | Unique with session                   |
| invite\_token             | `text` (unique)            | P4 token: `/evaluator/answer/{token}` |
| invite\_sent\_at          | `timestamptz`              | Optional                              |
| **answered\_at**          | `timestamptz`              | **Source of truth** for progress      |
| note                      | `text`                     | Admin note per evaluator              |
| created\_at / updated\_at | `timestamptz`              | —                                     |

- Progress logic (used by P1):
total = count(*) where session_id = ?
answered = count(*) where session_id = ? and answered_at IS NOT NULL

5) candidate_slots (P2 input, P3 compute, P4/P5 choices)

| Column        | Type                     | Notes          |      |          |
| ------------- | ------------------------ | -------------- | ---- | -------- |
| id            | `int` (identity, PK)     | —              |      |          |
| session\_id   | `int` (FK → sessions.id) | —              |      |          |
| slot\_date    | `date`                   | Candidate date |      |          |
| part\_of\_day | `text`                   | \`'AM'         | 'PM' | 'FULL'\` |
| sort\_order   | `int`                    | Display order  |      |          |
| created\_at   | `timestamptz`            | —              |      |          |

6) evaluator_answers (P4 submit, P3 aggregate)

| Column                 | Type                                | Notes                           |
| ---------------------- | ----------------------------------- | ------------------------------- |
| session\_evaluator\_id | `int` (FK → session\_evaluators.id) | (PK part)                       |
| candidate\_slot\_id    | `int` (FK → candidate\_slots.id)    | (PK part)                       |
| choice                 | `text`                              | `'O' (○)`, `'M' (△)`, `'X' (×)` |
| created\_at            | `timestamptz`                       | —                               |

- You can compute 全員○ by checking, per slot, whether all session evaluators have an 'O' for that slot.

7) client_response (P5 token; single choice)

| Column                        | Type                                       | Notes                              |
| ----------------------------- | ------------------------------------------ | ---------------------------------- |
| id                            | `int` (identity, PK)                       | —                                  |
| session\_id                   | `int` (unique, FK → sessions.id)           | One per session                    |
| invite\_token                 | `text` (unique)                            | P5 token: `/client/answer/{token}` |
| selected\_candidate\_slot\_id | `int` (FK → candidate\_slots.id, nullable) | Facility’s selected slot           |
| note                          | `text`                                     | Optional                           |
| answered\_at                  | `timestamptz`                              | When client submitted              |
| created\_at                   | `timestamptz`                              | —                                  |


## View for P1 Dashboard

### session_list_v (read-only)

### Columns:

- id (session id)

- facility_name

- purpose

- status

- confirmed_date — derived from client_response.selected_candidate_slot_id → candidate_slots.slot_date

- notion_url

- updated_at

- total_evaluators — count(*) from session_evaluators

- answered — count(*) from session_evaluators where answered_at IS NOT NULL

### Why a view?

- Keeps P1 simple & fast; the API can query one relation.

- Centralizes progress logic; no duplication in app code.

- Allows you to evolve internals without changing P1.

## Typical Flows
### P2: Create Session (Notion import → seed)

1. Normalize the Notion URL → notion_page_id

2. Upsert facilities by notion_page_id (set name, contact info, notion_url)

3. Upsert evaluators by email

4. Insert sessions (purpose/status/deadlines/notion_url)

5. Insert session_evaluators for all evaluators (tokens auto-generated)

6. Insert candidate_slots (date list; part_of_day='FULL' by default)

### P4: Evaluator submit

- Write evaluator_answers (0..N rows)

- Set session_evaluators.answered_at = now() (this drives P1 progress)

### P5: Client submit

- Set client_response.selected_candidate_slot_id + answered_at

- Optionally transition sessions.status → '確定'
