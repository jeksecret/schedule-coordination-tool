from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone, date

PURPOSE_OPTIONS = {"訪問調査", "聞き取り", "場面観察", "FB", "その他"}
DB_TO_SYMBOL: Dict[str, str] = {
    "O": "○", # OK
    "M": "△", # Maybe
    "X": "x", # NG
}
SYMBOL_TO_DB: Dict[str, str] = {
    "○": "O",
    "△": "M",
    "x": "X",
}
CHOICE_SYMBOLS: Set[str] = set(SYMBOL_TO_DB.keys())
CHOICE_DB_TOKENS: Set[str] = set(DB_TO_SYMBOL.keys())

def _get_session_with_facility(supabase, session_id: int) -> Dict[str, Any]:
    s_res = (
        supabase.table("sessions")
        .select(
            "id, facility_id, purpose, status, response_deadline, presentation_date, notion_url, "
            "facility_form_id, facility_form_view_url, facility_form_edit_url"
        )
        .eq("id", session_id)
        .single()
        .execute()
    )
    if not s_res.data:
        raise ValueError(f"Session {session_id} not found")
    s = s_res.data

    f_res = (
        supabase.table("facilities")
        .select("id, name, contact_name, contact_email, notion_url")
        .eq("id", s["facility_id"])
        .single()
        .execute()
    )
    f = f_res.data or {}

    return {
        "id": s["id"],
        "purpose": s.get("purpose"),
        "status": s.get("status"),
        "response_deadline": s.get("response_deadline"),
        "presentation_date": s.get("presentation_date"),
        "notion_url": s.get("notion_url"),
        "facility_form_view_url": s.get("facility_form_view_url"),
        "facility_form_edit_url": s.get("facility_form_edit_url"),
        "facility": {
            "id": f.get("id"),
            "name": f.get("name"),
            "contact_name": f.get("contact_name"),
            "contact_email": f.get("contact_email"),
            "notion_url": f.get("notion_url"),
        },
    }

def _get_session_evaluator_rows(supabase, session_id: int) -> List[Dict[str, Any]]:
    """
    session_evaluators: id, session_id, evaluator_id, answered_at, note.
    """
    return (
        supabase.table("session_evaluators")
        .select("id, evaluator_id, answered_at, note, evaluator_form_view_url, evaluator_form_edit_url, evaluator_form_id")
        .eq("session_id", session_id)
        .execute()
    ).data or []

def _build_evaluators(supabase, se_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ids = [r["evaluator_id"] for r in se_rows]
    if not ids:
        return []

    ev_map = {
        r["id"]: r
        for r in (
            supabase.table("evaluators")
            .select("id, name, email")
            .in_("id", ids)
            .execute()
        ).data or []
    }

    out: List[Dict[str, Any]] = []
    for row in se_rows:
        ev = ev_map.get(row["evaluator_id"], {})
        out.append({
            "id": row["evaluator_id"],
            "session_evaluator_id": row["id"],
            "name": ev.get("name"),
            "email": ev.get("email"),
            "answered_at": row.get("answered_at"),
            "note": row.get("note"),
            "form_id": row.get("evaluator_form_id"),
            "form_view_url": row.get("evaluator_form_view_url"),
            "form_edit_url": row.get("evaluator_form_edit_url"),
        })
    return out

def _get_candidate_slots(supabase, session_id: int) -> List[Dict[str, Any]]:
    return (
        supabase.table("candidate_slots")
        .select("id, slot_date, slot_label, sort_order")
        .eq("session_id", session_id)
        .order("sort_order", desc=False)
        .execute()
    ).data or []

def _get_answers_matrix_from_se(
    supabase,
    se_rows: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Optional[str]]]:
    """
    evaluator_responses: session_evaluator_id, candidate_slot_id, choice ('O'|'M'|'X')
    """
    if not se_rows:
        return {}

    se_id_to_eid = {r["id"]: r["evaluator_id"] for r in se_rows}
    se_ids = list(se_id_to_eid.keys())

    rows = (
        supabase.table("evaluator_responses")
        .select("session_evaluator_id, candidate_slot_id, choice")
        .in_("session_evaluator_id", se_ids)
        .execute()
    ).data or []

    matrix: Dict[str, Dict[str, Optional[str]]] = {}
    for r in rows:
        eid = se_id_to_eid.get(r["session_evaluator_id"])
        if eid is None:
            continue
        ekey = str(eid)
        skey = str(r["candidate_slot_id"])
        db_choice = str(r.get("choice") or "")
        symbol = DB_TO_SYMBOL.get(db_choice)
        matrix.setdefault(ekey, {})[skey] = symbol
    return matrix

def fetch_session_status(supabase, session_id: int) -> Dict[str, Any]:
    """
    Aggregate header, evaluators, slots, and answers for P3 (read-only).
    Matches current columns:
      - session_evaluators.note (not 'remark')
      - evaluator_responses(session_evaluator_id, candidate_slot_id, choice)
      - candidate_slots
    """
    session = _get_session_with_facility(supabase, session_id)
    se_rows = _get_session_evaluator_rows(supabase, session_id)
    evaluators = _build_evaluators(supabase, se_rows)
    slots = _get_candidate_slots(supabase, session_id)
    answers = _get_answers_matrix_from_se(supabase, se_rows)
    return {"session": session, "evaluators": evaluators, "slots": slots, "answers": answers}

def _resolve_session_evaluator_id(supabase, session_id: int, evaluator_id: int) -> int:
    """
    Look up session_evaluators.id by (session_id, evaluator_id).
    """
    res = (
        supabase.table("session_evaluators")
        .select("id")
        .eq("session_id", session_id)
        .eq("evaluator_id", evaluator_id)
        .single()
        .execute()
    )
    if not res.data:
        raise ValueError(f"Session evaluator not found for session={session_id}, evaluator={evaluator_id}")
    return int(res.data["id"])

def _session_slot_ids(supabase, session_id: int) -> Set[int]:
    """
    Return the valid candidate_slot ids for the given session to guard against cross-session updates.
    """
    rows = (
        supabase.table("candidate_slots")
        .select("id")
        .eq("session_id", session_id)
        .execute()
    ).data or []
    return {int(r["id"]) for r in rows if "id" in r}

def update_session(
    supabase,
    session_id: int,
    purpose: Optional[str],
    response_deadline: Optional[date],
    presentation_date: Optional[date],
) -> Dict[str, Any]:
    """
    Update session header fields:
      - purpose
      - response_deadline
      - presentation_date
    """
    updates: Dict[str, Any] = {}
    if purpose is not None:
      p = str(purpose).strip()
      if p:
          if p not in PURPOSE_OPTIONS:
              raise ValueError("Invalid purpose")
          updates["purpose"] = p
    if response_deadline is not None:
        updates["response_deadline"] = response_deadline.isoformat()
    if presentation_date is not None:
        updates["presentation_date"] = presentation_date.isoformat()
    if not updates:
        cur = (
            supabase.table("sessions")
            .select("id, purpose, response_deadline, presentation_date")
            .eq("id", session_id)
            .single()
            .execute()
        )
        if not cur.data:
            raise ValueError(f"Session {session_id} not found")
        return {"session": cur.data}

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    _ = (
        supabase.table("sessions")
        .update(updates)
        .eq("id", session_id)
        .execute()
    )
    sel = (
        supabase.table("sessions")
        .select("id, purpose, response_deadline, presentation_date")
        .eq("id", session_id)
        .single()
        .execute()
    )
    if not sel.data:
        raise ValueError(f"Session {session_id} not found after update")

    return {"session": sel.data}

def update_evaluator_responses(
    supabase,
    session_id: int,
    evaluator_id: int,
    note: Optional[str],
    answers: Dict[int, Optional[str]],
) -> Dict[str, Any]:
    """
    Apply admin edits for a single evaluator:
      - Update session_evaluators.note
      - Upsert evaluator_responses for non-empty choices
      - Delete evaluator_responses for empty/cleared choices
    """
    se_id = _resolve_session_evaluator_id(supabase, session_id, evaluator_id)
    valid_slot_ids = _session_slot_ids(supabase, session_id)

    # Track desired answer state per slot
    to_upsert: Dict[int, str] = {}
    to_delete: Set[int] = set()

    for sid, val in (answers or {}).items():
        if sid not in valid_slot_ids:
            continue

        if val is None:
            to_upsert.pop(sid, None)
            to_delete.add(sid)
            continue

        s = str(val).strip()
        if not s:
            to_upsert.pop(sid, None)
            to_delete.add(sid)
            continue

        if s in CHOICE_SYMBOLS:
            db_choice = SYMBOL_TO_DB[s]
        else:
            token = s.upper()
            if token in CHOICE_DB_TOKENS:
                db_choice = token
            else:
                continue

        to_upsert[sid] = db_choice
        to_delete.discard(sid)

    now_iso = datetime.now(timezone.utc).isoformat()
    if note is not None:
        _ = (
            supabase.table("session_evaluators")
            .update({"note": note, "updated_at": now_iso})
            .eq("id", se_id)
            .execute()
        )
    if to_upsert:
        _ = (
            supabase.table("evaluator_responses")
            .upsert(
                [
                    {
                        "session_evaluator_id": se_id,
                        "candidate_slot_id": sid,
                        "choice": choice,
                    }
                    for sid, choice in to_upsert.items()
                ],
                on_conflict="session_evaluator_id,candidate_slot_id",
                ignore_duplicates=False,
            )
            .execute()
        )
    if to_delete:
        _ = (
            supabase.table("evaluator_responses")
            .delete()
            .eq("session_evaluator_id", se_id)
            .in_("candidate_slot_id", sorted(to_delete))
            .execute()
        )
    if note is None:
        _ = (
            supabase.table("session_evaluators")
            .update({"updated_at": now_iso})
            .eq("id", se_id)
            .execute()
        )
    return {
        "session_id": session_id,
        "evaluator_id": evaluator_id,
        "updated_note": note,
        "upserted_count": len(to_upsert),
        "deleted_count": len(to_delete),
    }

def check_slot_everyone_ok(supabase, session_id: int, slot_id: int) -> Dict[str, Any]:
    """
    Check whether all evaluators for the session answered 'O' for the given slot.
    """
    slot = (
        supabase.table("candidate_slots")
        .select("id")
        .eq("id", slot_id)
        .eq("session_id", session_id)
        .single()
        .execute()
    )
    if not slot.data:
        raise ValueError("Slot not found for this session")

    se_rows = _get_session_evaluator_rows(supabase, session_id)
    if not se_rows:
        return {"slot_id": slot_id, "everyone_ok": False}

    se_ids = [r["id"] for r in se_rows]
    ans_rows = (
        supabase.table("evaluator_responses")
        .select("session_evaluator_id, choice")
        .in_("session_evaluator_id", se_ids)
        .eq("candidate_slot_id", slot_id)
        .execute()
    ).data or []

    ok_ids = {r["session_evaluator_id"] for r in ans_rows if str(r.get("choice") or "").upper() == "O"}
    everyone_ok = len(ok_ids) == len(se_ids)

    return {"slot_id": slot_id, "everyone_ok": everyone_ok}
