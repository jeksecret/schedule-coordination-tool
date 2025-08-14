# Database Schema (P1–P5)

Progress = **answered / total** derived from `session_evaluators.answered_at`.

```mermaid
erDiagram
  FACILITIES ||--o{ SESSIONS : has
  SESSIONS ||--o{ SESSION_EVALUATORS : includes
  EVALUATORS ||--o{ SESSION_EVALUATORS : participates
  SESSIONS ||--o{ CANDIDATE_SLOTS : offers
  SESSION_EVALUATORS ||--o{ EVALUATOR_ANSWERS : answers
  CANDIDATE_SLOTS ||--o{ EVALUATOR_ANSWERS : for
  SESSIONS ||--|| CLIENT_RESPONSE : confirms
  SESSIONS ||--o{ SESSION_LIST_V : feeds

  FACILITIES {
    int id
    string notion_page_id
    string notion_url
    string name
    string contact_name
    string contact_email
    datetime last_notion_sync_at
    datetime created_at
    datetime updated_at
  }

  SESSIONS {
    int id
    int facility_id
    string purpose
    string status
    date response_deadline
    date presentation_date
    string notion_url
    datetime created_at
    datetime updated_at
  }

  EVALUATORS {
    int id
    string name
    string email
    datetime created_at
    datetime updated_at
  }

  SESSION_EVALUATORS {
    int id
    int session_id
    int evaluator_id
    string invite_token
    datetime invite_sent_at
    datetime answered_at
    string note
    datetime created_at
    datetime updated_at
  }

  CANDIDATE_SLOTS {
    int id
    int session_id
    date slot_date
    string part_of_day
    int sort_order
    datetime created_at
  }

  EVALUATOR_ANSWERS {
    int session_evaluator_id
    int candidate_slot_id
    string choice
    datetime created_at
  }

  CLIENT_RESPONSE {
    int id
    int session_id
    string invite_token
    int selected_candidate_slot_id
    string note
    datetime answered_at
    datetime created_at
  }

  SESSION_LIST_V {
    int id
    string facility_name
    string purpose
    string status
    date confirmed_date
    string notion_url
    datetime updated_at
    int total_evaluators
    int answered
  }
