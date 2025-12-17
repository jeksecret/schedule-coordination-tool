from typing import Dict, Any, List, Tuple
import json, urllib.request, os, socket, re
from urllib.error import URLError
from app.services.notion.facility_info_service import fetch_facility_info

_webhook_url = os.environ.get("MAKE_GENERATE_FACILITY_EMAIL")
if not _webhook_url:
    raise RuntimeError("MAKE_GENERATE_FACILITY_EMAIL is not set")

_default_timeout = int(os.environ.get("MAKE_HTTP_TIMEOUT_SECONDS", "120"))

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
    s_res = (
        supabase.table("sessions")
        .select("id, facility_id, purpose, response_deadline, presentation_date, notion_url")
        .eq("id", session_id)
        .single()
        .execute()
    )
    if not s_res.data:
        raise ValueError(f"Session {session_id} not found")
    return s_res.data

def _fetch_facility(supabase, facility_id: int) -> Dict[str, Any]:
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

def _fetch_evaluators_for_session(supabase, session_id: int) -> List[Dict[str, Any]]:
    """
    Fetch evaluators linked to the given session, with email normalized as list.
    """
    se_res = (
        supabase.table("session_evaluators")
        .select("evaluator_id")
        .eq("session_id", session_id)
        .execute()
    )
    ids = [row["evaluator_id"] for row in se_res.data or [] if "evaluator_id" in row]
    if not ids:
        return []
    ev_res = (
        supabase.table("evaluators")
        .select("id, name, email")
        .in_("id", ids)
        .execute()
    )
    ev_data = ev_res.data or []

    evaluators: List[Dict[str, Any]] = []
    for e in ev_data:
        emails = _extract_emails(e.get("email") or "")
        evaluators.append({
            "id": e.get("id"),
            "name": e.get("name"),
            "emails": emails,
        })
    return evaluators

def _fetch_slots_by_ids(supabase, session_id: int, ids: List[int]) -> List[Dict[str, Any]]:
    if not ids: return []
    cs_res = (
        supabase.table("candidate_slots")
        .select("id, slot_date, slot_label, sort_order")
        .eq("session_id", session_id)
        .in_("id", ids)
        .order("sort_order", desc=False)
        .execute()
    )
    return cs_res.data or []

def build_make_payload(supabase, session_id: int, candidate_slot_ids: List[int]) -> Dict[str, Any]:
    s = _fetch_session(supabase, session_id)
    f = _fetch_facility(supabase, s["facility_id"])
    evaluators = _fetch_evaluators_for_session(supabase, session_id)
    slots = _fetch_slots_by_ids(supabase, session_id, candidate_slot_ids)

    if f.get("name"):
        f["name"] = _normalize_single_line(f["name"])

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
        "purpose": s.get("purpose"),
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
                "email": e.get("emails")
            }
            for e in evaluators
        ],
        "selected_slots": [
            {
                "id": r.get("id"),
                "slot_date": r.get("slot_date"),
                "slot_label": r.get("slot_label"),
                "sort_order": r.get("sort_order"),
            }
            for r in slots
        ],
    }
    return payload

def post_to_make_webhook(payload: Dict[str, Any], timeout_sec: int = _default_timeout) -> Tuple[int, str]:
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
            status = resp.getcode()
            text = resp.read().decode("utf-8")
            return status, text
    except (socket.timeout, URLError) as e:
        raise TimeoutError("Make webhook request timed out") from e
