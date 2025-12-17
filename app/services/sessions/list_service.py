from typing import Optional
import unicodedata
import re

def normalize_text_for_search(text: str) -> str:
    """
    Normalizes Japanese and mixed-width text for reliable searching.
    - Converts full-width to half-width (NFKC)
    - Removes invisible control characters
    - Replaces all whitespace/newlines/full-width spaces with a single space
    - Converts to lowercase
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)
    text = re.sub(r"[\s\u3000]+", " ", text)
    return text.lower().strip()

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

    Uses DB-side pagination for performance & stability.
    """
    offset = (page - 1) * page_size
    limit_start = offset
    limit_end = offset + page_size - 1

    q = (
        supabase
        .table("session_list_v")
        .select(
            "id, facility_name, purpose, status, confirmed_date, notion_url, updated_at, "
            "total_evaluators, answered",
            count="exact",
        )
        .order("id", desc=True)
    )

    if purpose:
        q = q.eq("purpose", purpose)

    if status:
        q = q.eq("status", status)

    if facility:
        norm = normalize_text_for_search(facility.strip())
        q = q.ilike("facility_name_norm", f"%{norm}%")

    # DB-side pagination
    q = q.range(limit_start, limit_end)

    res = q.execute()

    items = res.data or []
    total = res.count or 0

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
