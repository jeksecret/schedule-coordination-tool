from typing import List, Dict, Any
from datetime import date
from pydantic import HttpUrl
from app.services.notion.facility_info_service import fetch_facility_info

def upsert_facility(supabase, *, notion_url: HttpUrl, info: Dict[str, Any]) -> int:
    """
    Upsert by notion_page_id and return facilities.id (int).
    """
    payload = {
        "notion_page_id": info.get("notion_page_id"),
        "notion_url": str(notion_url),
        "name": info.get("facility_name") or "",
        "contact_name": (info.get("contact_person") or {}).get("name") or None,
        "contact_email": (info.get("contact_person") or {}).get("email") or None,
    }
    res = (
        supabase.table("facilities")
        .upsert(payload, on_conflict="notion_page_id", returning="representation")
        .execute()
    )
    if res.data and len(res.data) > 0 and "id" in res.data[0]:
        return res.data[0]["id"]

    sel = (
        supabase.table("facilities")
        .select("id")
        .eq("notion_page_id", info.get("notion_page_id"))
        .single()
        .execute()
    )
    return sel.data["id"]

def upsert_evaluators(supabase, evaluators: List[Dict[str, str]]) -> List[int]:
    """Upsert evaluators by email; return list of evaluator ids."""
    rows = [
        {"name": ev.get("name") or "", "email": ev["email"]}
        for ev in (evaluators or [])
        if ev.get("email")
    ]
    if not rows:
        return []
    _ = (
        supabase.table("evaluators")
        .upsert(rows, on_conflict="email", returning="minimal")
        .execute()
    )
    emails = [r["email"] for r in rows]
    res = (
        supabase.table("evaluators")
        .select("id,email")
        .in_("email", emails)
        .execute()
    )
    return [r["id"] for r in (res.data or [])]

def create_session_row(
    supabase,
    *,
    facility_id: int,
    purpose: str,
    response_deadline: date,
    presentation_date: date,
    notion_url: HttpUrl,
) -> int:
    STATUS_LABEL = "起案中"
    res = (
        supabase.table("sessions")
        .insert(
            {
                "facility_id": facility_id,
                "purpose": purpose,
                "status": STATUS_LABEL,
                # coerce to ISO strings
                "response_deadline": response_deadline.isoformat(),
                "presentation_date": presentation_date.isoformat(),
                "notion_url": str(notion_url),
            },
            returning="representation",
        )
        .execute()
    )
    return res.data[0]["id"]

def link_session_evaluators(supabase, session_id: int, evaluator_ids: List[int]) -> None:
    if not evaluator_ids:
        return
    supabase.table("session_evaluators").insert(
        [{"session_id": session_id, "evaluator_id": eid} for eid in evaluator_ids]
    ).execute()

def insert_candidate_slots(
    supabase,
    session_id: int,
    candidate_slots: List[Dict[str, Any]],
) -> None:
    rows = []
    for i, s in enumerate(candidate_slots or []):
        d = s.get("slot_date")
        lbl = (s.get("slot_label") or "").strip()
        if not d or not lbl:
            continue
        d_iso = d.isoformat()
        rows.append(
            {
                "session_id": session_id,
                "slot_date": d_iso,
                "slot_label": lbl,
                "sort_order": i,
            }
        )
    if rows:
        supabase.table("candidate_slots").insert(rows).execute()

def create_session_with_notion(
    supabase,
    *,
    notion_url: HttpUrl,
    purpose: str,
    response_deadline: date,
    presentation_date: date,
    candidate_slots: List[Dict[str, Any]],
) -> int:
    """
    1) fetch Notion facility info
    2) upsert facilities/evaluators
    3) create session
    4) link session_evaluators
    5) insert candidate_slots
    """
    info = fetch_facility_info(notion_url)
    facility_id = upsert_facility(supabase, notion_url=notion_url, info=info)
    evaluator_ids = upsert_evaluators(supabase, info.get("evaluators") or [])

    session_id = create_session_row(
        supabase,
        facility_id=facility_id,
        purpose=purpose,
        response_deadline=response_deadline,
        presentation_date=presentation_date,
        notion_url=notion_url,
    )

    link_session_evaluators(supabase, session_id, evaluator_ids)
    insert_candidate_slots(supabase, session_id, candidate_slots)
    return session_id
