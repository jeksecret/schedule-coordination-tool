from typing import Dict, Any, List, Optional
from urllib.error import URLError
import json
import os
import urllib.request
import socket

_default_timeout = int(os.environ.get("MAKE_HTTP_TIMEOUT_SECONDS", "120"))
_webhook_url = os.environ.get("MAKE_ON_CLIENT_RESPONSE")
if not _webhook_url:
    raise RuntimeError("MAKE_ON_CLIENT_RESPONSE is not set")

def _get_session(supabase, session_id: int) -> Dict[str, Any]:
    res = (
        supabase.table("sessions")
        .select("id, facility_id, purpose, status, response_deadline, presentation_date, notion_url")
        .eq("id", session_id)
        .single()
        .execute()
    )
    if not res.data:
        raise ValueError(f"Session {session_id} not found")
    return res.data

def _get_facility(supabase, facility_id: int) -> Dict[str, Any]:
    res = (
        supabase.table("facilities")
        .select("id, name, contact_name, contact_email, notion_url")
        .eq("id", facility_id)
        .single()
        .execute()
    )
    if not res.data:
        raise ValueError(f"Facility {facility_id} not found")
    return res.data

def _get_session_evaluators(supabase, session_id: int) -> List[Dict[str, Any]]:
    se = (
        supabase.table("session_evaluators")
        .select("evaluator_id")
        .eq("session_id", session_id)
        .execute()
    )
    ids = [row["evaluator_id"] for row in (se.data or [])]
    if not ids:
        return []
    ev = (
        supabase.table("evaluators")
        .select("id, name, email")
        .in_("id", ids)
        .execute()
    )
    return ev.data or []

def _get_candidate_slot(supabase, slot_id: int) -> Optional[Dict[str, Any]]:
    res = (
        supabase.table("candidate_slots")
        .select("id, slot_date, slot_label, sort_order")
        .eq("id", slot_id)
        .single()
        .execute()
    )
    return res.data or None

def _get_client_response(supabase, session_id: int) -> Optional[Dict[str, Any]]:
    res = (
        supabase.table("client_responses")
        .select("id, note, answered_at, selected_candidate_slot_id")
        .eq("session_id", session_id)
        .single()
        .execute()
    )
    return res.data or None

def _build_contact_emails(facility_row: Dict[str, Any]) -> List[str]:
    emails: List[str] = []
    if facility_row.get("contact_email"):
        emails.append(facility_row["contact_email"])
    if isinstance(facility_row.get("contact_emails"), list):
        emails.extend([e for e in facility_row["contact_emails"] if e])
    uniq, seen = [], set()
    for e in emails:
        k = (e or "").strip().lower()
        if k and k not in seen:
            uniq.append(e)
            seen.add(k)
    return uniq

def build_make_payload(
    supabase,
    *,
    session_id: int,
    selected_candidate_slot_id: Optional[int],
) -> List[Dict[str, Any]]:
    s = _get_session(supabase, session_id)
    f = _get_facility(supabase, s["facility_id"])
    evaluators = _get_session_evaluators(supabase, session_id)

    cr = _get_client_response(supabase, session_id)
    client_response_id = cr.get("id") if cr else None
    client_note = cr.get("note") if cr else None
    client_answered_at = cr.get("answered_at") if cr else None
    stored_slot_id = cr.get("selected_candidate_slot_id") if cr else None

    preferred_slot = None
    slot_id = selected_candidate_slot_id or stored_slot_id
    if slot_id:
        preferred_slot = _get_candidate_slot(supabase, slot_id)

    payload = [
        {
            "session_id": s["id"],
            "purpose": s.get("purpose"),
            "response_deadline": s.get("response_deadline"),
            "presentation_date": s.get("presentation_date"),
            "facility": {
                "name": f.get("name"),
                "contact_name": f.get("contact_name"),
                "contact_emails": _build_contact_emails(f),
                "notion_url": f.get("notion_url"),
            },
            "evaluators": evaluators,
            "client_response": {
                "id": client_response_id,
                "preferred_slot": preferred_slot,
                "client_note": client_note,
                "client_answered_at": client_answered_at,
            },
        }
    ]
    return payload

def post_to_make_webhook(payload: Dict[str, Any], timeout_sec: int = _default_timeout) -> int:
    """POST JSON to Make webhook; returns HTTP status code."""
    # Note: ensure_ascii=False allows non-ASCII characters (e.g., Japanese text) to be encoded directly in the JSON payload.
    # The payload is encoded as UTF-8 and the Content-Type header is set accordingly.
    # Ensure the Make webhook endpoint can process UTF-8 encoded JSON.
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        _webhook_url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return resp.getcode()
    except (socket.timeout, URLError) as e:
        raise TimeoutError("Make webhook request timed out") from e
