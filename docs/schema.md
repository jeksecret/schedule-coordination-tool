# Database Schema


```mermaid
erDiagram
  FACILITIES ||--o{ SESSIONS : has
  SESSIONS   ||--o{ CANDIDATE_SLOTS : has
  SESSIONS   ||--o{ SESSION_EVALUATORS : has
  EVALUATORS ||--o{ SESSION_EVALUATORS : assigned_to
  SESSION_EVALUATORS ||--o{ EVALUATOR_RESPONSES : answers
  CANDIDATE_SLOTS    ||--o{ EVALUATOR_RESPONSES : answered_for
  SESSIONS ||--o| CLIENT_RESPONSES : "has (0..1)"
  CLIENT_RESPONSES ||--|| CANDIDATE_SLOTS : selects

  FACILITIES {
    int id PK
    text notion_page_id
    text notion_url
    text name
    text contact_name
    text contact_email
    timestamptz created_at
    timestamptz updated_at
  }

  SESSIONS {
    int id PK
    int facility_id FK
    purpose_enum purpose
    status_enum status
    date response_deadline
    date presentation_date
    text notion_url
    timestamptz created_at
    timestamptz updated_at
  }

  CANDIDATE_SLOTS {
    int id PK
    int session_id FK
    date slot_date
    text slot_label
    int sort_order
    timestamptz created_at
  }

  SESSION_EVALUATORS {
    int id PK
    int session_id FK
    int evaluator_id FK
    text invite_token
    timestamptz answered_at
    text note
    text evaluator_form_id
    text evaluator_form_view_url
    text evaluator_form_edit_url
    timestamptz created_at
    timestamptz updated_at
  }

  EVALUATORS {
    int id PK
    text name
    text email
    timestamptz created_at
    timestamptz updated_at
  }

  EVALUATOR_RESPONSES {
    int session_evaluator_id FK
    int candidate_slot_id FK
    text choice
    timestamptz created_at
  }

  CLIENT_RESPONSES {
    int id PK
    int session_id FK
    int selected_candidate_slot_id FK
    text note
    timestamptz answered_at
    timestamptz created_at
  }

%% Notes:
%% - CLIENT_RESPONSES.session_id must be UNIQUE (only one client response per session).
%% - CLIENT_RESPONSES.selected_candidate_slot_id is REQUIRED (must always point to a candidate slot).
%% - EVALUATOR_RESPONSES has a COMPOSITE PK: (session_evaluator_id, candidate_slot_id).
%% - SESSION_EVALUATORS.invite_token is UNIQUE.
%% - EVALUATORS.email and FACILITIES.notion_page_id are UNIQUE.
%% - SESSIONS.purpose and SESSIONS.status are enums (status default = '起案中').
