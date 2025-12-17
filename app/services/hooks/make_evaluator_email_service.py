from typing import Dict, Any, List
from urllib.error import URLError
import json
import os
import urllib.request
import socket
import secrets
import re
from app.services.notion.facility_info_service import fetch_facility_info

_default_timeout = int(os.environ.get("MAKE_HTTP_TIMEOUT_SECONDS", "120"))
_webhook_url = os.environ.get("MAKE_GENERATE_EVALUATOR_EMAIL")
if not _webhook_url:
    raise RuntimeError("MAKE_GENERATE_EVALUATOR_EMAIL is not set")

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", re.IGNORECASE)

def _extract_emails(text: str) -> List[str]:
    """Extract all emails from arbitrary text (handles commas/newlines/etc)."""
    if not text:
        return []
    norm = (
        text.replace("\r\n", " ")
            .replace("\n", " ")
            .replace("、", " ")
            .replace(";", " ")
            .replace(",", " ")
    )
    return [m.strip() for m in _EMAIL_RE.findall(norm)]

def _merge_unique_emails(*lists: List[str]) -> List[str]:
    seen, out = set(), []
    for lst in lists:
        for e in lst or []:
            k = e.strip().lower()
            if k and k not in seen:
                seen.add(k)
                out.append(e.strip())
    return out

def _normalize_single_line(text: str) -> str:
    """Convert multiline or irregular text into a single clean line."""
    if not text:
        return ""
    return re.sub(r"[\r\n]+", " ", text).strip()

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
    Fetch evaluators linked to the given session, with email normalized as list.
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

        emails = _extract_emails(ev.get("email") or "")
        out.append({
            "id": eid,
            "name": ev.get("name"),
            "emails": emails,
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

    if f.get("name"):
        f["name"] = _normalize_single_line(f["name"])

    _ensure_invite_tokens(supabase, session_id)

    evaluators = _fetch_evaluators_for_session(supabase, session_id)
    slots = _fetch_candidate_slots(supabase, session_id)

    db_emails = _extract_emails(f.get("contact_email") or "")
    notion_emails: List[str] = []
    notion_url = f.get("notion_url") or s.get("notion_url") or ""
    if notion_url:
        try:
            info = fetch_facility_info(notion_url)
            notion_emails = info.get("contact_emails") or _extract_emails(
                (info.get("contact_person") or {}).get("email", "")
            )
        except Exception:
            pass

    recipients = _merge_unique_emails(db_emails, notion_emails)

    payload = {
        "session_id": s["id"],
        "purpose": s["purpose"],
        "response_deadline": s.get("response_deadline"),
        "presentation_date": s.get("presentation_date"),
        "facility": {
            "name": f.get("name"),
            "contact_name": f.get("contact_name"),
            "contact_emails": recipients,
            "notion_url": f.get("notion_url"),
        },
        "evaluators": [
            {
                "id": e.get("id"),
                "name": e.get("name"),
                "email": e.get("emails"),
                "invite_token": e.get("invite_token"),
            }
            for e in (evaluators)
        ],
        "candidate_slots": [
            {
                "id": r.get("id"),
                "slot_date": r.get("slot_date"),
                "slot_label": r.get("slot_label"),
                "sort_order": r.get("sort_order"),
            }
            for r in (slots)
        ],
    }
    return payload

def post_to_make_webhook(payload: Dict[str, Any], timeout_sec: int = _default_timeout) -> int:
    """
    POST to Make and return (status_code, response_text).
    Raises TimeoutError on socket/URL timeout.
    """
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
