from typing import Dict, Any, List
from urllib.error import URLError
import json
import os
import urllib.request
import socket
import secrets

_default_timeout = int(os.environ.get("MAKE_HTTP_TIMEOUT_SECONDS", "120"))
_webhook_url = os.environ.get("MAKE_GENERATE_EVALUATOR_EMAIL")
if not _webhook_url:
    raise RuntimeError("MAKE_GENERATE_EVALUATOR_EMAIL is not set")

def _fetch_session(supabase, session_id: int) -> Dict[str, Any]:
    """Load session fields for email/template."""
    s_res = (
        supabase.table("sessions")
        .select("id, facility_id, purpose, status, response_deadline, presentation_date, notion_url")
        .eq("id", session_id)
        .single()
        .execute()
    )
    if not s_res.data:
        raise ValueError(f"Session {session_id} not found")
    return s_res.data

def _fetch_facility(supabase, facility_id: int) -> Dict[str, Any]:
    """Load facility fields for email/template."""
    f_res = (
        supabase.table("facilities")
        .select("id, name, contact_name, contact_email, notion_url")
        .eq("id", facility_id)
        .single()
        .execute()
    )
    if not f_res.data:
        raise ValueError(f"Facility {facility_id} not found")
    return f_res.data

def _ensure_invite_tokens(supabase, session_id: int) -> None:
    rows = (
        supabase.table("session_evaluators")
        .select("id, invite_token")
        .eq("session_id", session_id)
        .execute()
    ).data or []
    to_set = []
    for r in rows:
        tok = (r.get("invite_token") or "").strip()
        if not tok:
            to_set.append({"id": r["id"], "invite_token": secrets.token_urlsafe(16)})
    if to_set:
        _ = (
            supabase.table("session_evaluators")
            .upsert(to_set, on_conflict="id")
            .execute()
        )

def _fetch_evaluators_for_session(supabase, session_id: int) -> List[Dict[str, Any]]:
    """
    Return [{ id, name, email, invite_token }] for this session.
    """
    se_rows = (
        supabase.table("session_evaluators")
        .select("evaluator_id, invite_token")
        .eq("session_id", session_id)
        .execute()
    ).data or []

    evaluator_ids = [r["evaluator_id"] for r in se_rows if "evaluator_id" in r]
    if not evaluator_ids:
        return []

    ev_rows = (
        supabase.table("evaluators")
        .select("id, name, email")
        .in_("id", evaluator_ids)
        .execute()
    ).data or []
    ev_map = {r["id"]: r for r in ev_rows}

    out: List[Dict[str, Any]] = []
    for se in se_rows:
        eid = se["evaluator_id"]
        ev = ev_map.get(eid, {})
        out.append({
            "id": eid,
            "name": ev.get("name"),
            "email": ev.get("email"),
            "invite_token": se.get("invite_token"),
        })
    return out

def _fetch_candidate_slots(supabase, session_id: int) -> List[Dict[str, Any]]:
    """
    Return candidate slots ordered by sort_order ascending.
    """
    cs_res = (
        supabase.table("candidate_slots")
        .select("id, slot_date, slot_label, sort_order")
        .eq("session_id", session_id)
        .order("sort_order", desc=False)
        .execute()
    )
    return cs_res.data or []

def build_make_payload(supabase, session_id: int) -> Dict[str, Any]:
    """
    Build payload for Make:
      - session id / facility / purpose / deadlines
      - evaluators [{id,name,email,invite_token}]
      - candidate_slots [{id,date,label,order}]
    """
    s = _fetch_session(supabase, session_id)
    f = _fetch_facility(supabase, s["facility_id"])

    _ensure_invite_tokens(supabase, session_id)

    evaluators = _fetch_evaluators_for_session(supabase, session_id)
    slots = _fetch_candidate_slots(supabase, session_id)

    payload = {
        "session_id": s["id"],
        "purpose": s["purpose"],
        "response_deadline": s.get("response_deadline"),
        "presentation_date": s.get("presentation_date"),
        "facility": {
            "name": f.get("name"),
            "contact_name": f.get("contact_name"),
            "contact_email": f.get("contact_email"),
            "notion_url": f.get("notion_url"),
        },
        "evaluators": [
            {
                "id": e.get("id"),
                "name": e.get("name"),
                "email": e.get("email"),
                "invite_token": e.get("invite_token"),
            }
            for e in (evaluators or [])
        ],
        "candidate_slots": [
            {
                "id": r.get("id"),
                "slot_date": r.get("slot_date"),
                "slot_label": r.get("slot_label"),
                "sort_order": r.get("sort_order"),
            }
            for r in (slots or [])
        ],
    }
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

def mark_session_status(supabase, session_id: int, status: str) -> None:
    """Update sessions.status."""
    _ = (
        supabase.table("sessions")
        .update({"status": status})
        .eq("id", session_id)
        .execute()
    )
