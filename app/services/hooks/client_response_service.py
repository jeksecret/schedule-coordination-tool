from typing import Optional, Dict, Any
from datetime import datetime, timezone
from .client_response_notify_service import build_make_payload

CONFIRMED_STATUS = "確定"

def _has_existing_response(supabase, session_id: int) -> bool:
    res = (
        supabase.table("client_responses")
        .select("session_id")
        .eq("session_id", session_id)
        .limit(1)
        .execute()
    )
    return bool(res.data)

def _slot_belongs_to_session(supabase, session_id: int, slot_id: int) -> bool:
    res = (supabase.table("candidate_slots")
           .select("id")
           .eq("session_id", session_id)
           .eq("id", slot_id)
           .single()
           .execute())
    return bool(res.data)

def insert_client_response(
    supabase,
    *,
    session_id: int,
    selected_candidate_slot_id: Optional[int],
    note: Optional[str] = None,
) -> Dict[str, Any]:
    if _has_existing_response(supabase, session_id):
        raise ValueError("This form has already been submitted for the session.")

    if selected_candidate_slot_id is not None:
        if not _slot_belongs_to_session(supabase, session_id, selected_candidate_slot_id):
            raise ValueError("Selected slot does not belong to the session")

    now_iso = datetime.now(timezone.utc).isoformat()

    row = {
        "session_id": session_id,
        "selected_candidate_slot_id": selected_candidate_slot_id,
        "note": note,
        "answered_at": now_iso,
        "created_at": now_iso,
    }

    res = supabase.table("client_responses").insert(row).execute()

    try:
        if res.data:
            mark_session_status(supabase, session_id, CONFIRMED_STATUS)
    except Exception:
        pass

    client_response_payload = build_make_payload(
        supabase,
        session_id=session_id,
        selected_candidate_slot_id=selected_candidate_slot_id,
    )

    return {
        "ok": True,
        "updated_count": len(res.data or []),
        "session_id": session_id,
        "client_response_payload": client_response_payload,
    }

def mark_session_status(supabase, session_id: int, status: str) -> None:
    """Update sessions.status."""
    _ = (
        supabase.table("sessions")
        .update({"status": status})
        .eq("id", session_id)
        .execute()
    )
