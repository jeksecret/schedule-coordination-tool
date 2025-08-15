from typing import Optional

def fetch_session_list(
    supabase,
    *,
    purpose: Optional[str],
    status: Optional[str],
    facility: Optional[str],
    page: int,
    page_size: int,
):
    """
    Reads from session_list_v, which is backed by:
        sessions, facilities, session_evaluators (answered_at), client_responses, candidate_slots
    """
    offset = (page - 1) * page_size
    end = offset + page_size - 1

    q = (
        supabase
        .table("session_list_v")
        .select(
            "id, facility_name, purpose, status, confirmed_date, notion_url, updated_at, "
            "total_evaluators, answered",
            count="exact",
        )
        .order("updated_at", desc=True)
    )

    if purpose:
        q = q.eq("purpose", purpose)
    if status:
        q = q.eq("status", status)
    if facility:
        q = q.ilike("facility_name", f"%{facility}%")

    # server-side pagination
    q = q.range(offset, end)

    res = q.execute()
    items = res.data or []
    total = getattr(res, "count", None)
    if total is None:
        total = len(items)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
