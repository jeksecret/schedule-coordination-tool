from typing import Optional, Dict, Any

def fetch_confirmation_summary(
    supabase,
    *,
    session_id: int,
) -> Optional[Dict[str, Any]]:
    """
    Returns the latest confirmation summary row for the given session_id,
    or None if no row exists.
    """
    res = (
        supabase
        .table("session_confirmation_summary_v")
        .select("*")
        .eq("session_id", session_id)
        .order("client_answered_at", desc=True, nullsfirst=False)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None
