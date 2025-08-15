from typing import Dict, Optional, List, Any
from datetime import datetime, timezone

ALLOWED = {"O", "M", "X"}
WAITING_FOR_CLIENT_STATUS = "事業所待ち"

def _load_slot_ids_for_session(supabase, session_id: int) -> set[int]:
    rows = (
        supabase.table("candidate_slots")
        .select("id")
        .eq("session_id", session_id)
        .execute()
    ).data or []
    return {int(r["id"]) for r in rows if "id" in r}

def _resolve_by_token(supabase, token: str) -> Dict[str, int]:
    se = (
        supabase.table("session_evaluators")
        .select("id, session_id, evaluator_id")
        .eq("invite_token", token)
        .single()
        .execute()
    )
    if not se.data:
        raise ValueError("Invalid token")

    return {
        "session_id": int(se.data["session_id"]),
        "evaluator_id": int(se.data["evaluator_id"]),
        "session_evaluator_id": int(se.data["id"]),
    }

def _all_evaluators_answered(supabase, session_id: int) -> bool:
    """Return True if every evaluator for the session has answered_at set."""
    total_q = (
        supabase.table("session_evaluators")
        .select("id", count="exact")
        .eq("session_id", session_id)
    ).execute()
    total = getattr(total_q, "count", None)
    if total is None:
        total = len(total_q.data or [])

    answered_q = (
        supabase.table("session_evaluators")
        .select("id", count="exact")
        .eq("session_id", session_id)
        .not_.is_("answered_at", None)
    ).execute()
    answered = getattr(answered_q, "count", None)
    if answered is None:
        answered = len(answered_q.data or [])

    return total > 0 and total == answered

def insert_evaluator_response(
    supabase,
    *,
    token: str,
    answers: Dict[int, str],
    note: Optional[str] = None,
) -> Dict[str, Any]:
    ids = _resolve_by_token(supabase, token)
    session_id = ids["session_id"]
    evaluator_id = ids["evaluator_id"]
    session_evaluator_id = ids["session_evaluator_id"]

    now_iso = datetime.now(timezone.utc).isoformat()
    update_data = {"answered_at": now_iso}
    if note is not None:
        update_data["note"] = note

    res = (
        supabase.table("session_evaluators")
        .update(update_data)
        .eq("id", session_evaluator_id)
        .is_("answered_at", None)
        .execute()
    )
    if not res.data:
        raise ValueError("This evaluator has already submitted a response.")

    allowed_slot_ids = _load_slot_ids_for_session(supabase, session_id)
    rows: List[Dict[str, Any]] = []
    for raw_sid, raw_token in (answers or {}).items():
        try:
            sid = int(raw_sid)
        except Exception:
            continue
        token_up = str(raw_token).strip().upper()
        if sid in allowed_slot_ids and token_up in ALLOWED:
            rows.append({
                "session_evaluator_id": session_evaluator_id,
                "candidate_slot_id": sid,
                "choice": token_up,
                "created_at": now_iso,
            })

    if rows:
        _ = (
            supabase.table("evaluator_responses")
            .upsert(rows, on_conflict="session_evaluator_id,candidate_slot_id")
            .execute()
        )

    try:
        if _all_evaluators_answered(supabase, session_id):
            mark_session_status(supabase, session_id, WAITING_FOR_CLIENT_STATUS)
    except Exception:
        pass

    return {
        "ok": True,
        "token": token,
        "session_id": session_id,
        "evaluator_id": evaluator_id,
        "session_evaluator_id": session_evaluator_id,
        "answered_at": now_iso,
        "upserted_count": len(rows),
    }

def mark_session_status(supabase, session_id: int, status: str) -> None:
    """Update sessions.status."""
    _ = (
        supabase.table("sessions")
        .update({"status": status})
        .eq("id", session_id)
        .execute()
    )
