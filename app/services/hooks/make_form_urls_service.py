from typing import Optional, Dict, Any

def _resolve_session_evaluator_id(supabase, session_id: int, evaluator_id: int) -> int:
    """
    Return the `session_evaluators.id` for a given (session_id, evaluator_id).
    """
    row = (
        supabase.table("session_evaluators")
        .select("id")
        .eq("session_id", session_id)
        .eq("evaluator_id", evaluator_id)
        .single()
        .execute()
    ).data
    if not row:
        raise ValueError("Session evaluator not found")
    return int(row["id"])

def save_urls_for_session_evaluator(
    supabase,
    *,
    session_id: int,
    form_id: str,
    view_url: str,
    edit_url: str,
    session_evaluator_id: Optional[int] = None,
    evaluator_id: Optional[int] = None,
) -> None:
    """
    Persist per-evaluator Google Form URLs to `session_evaluators`.
    Exactly one of `session_evaluator_id` or `evaluator_id` must be provided.
    If only `evaluator_id` is given, this function resolves the row id using
    the provided `session_id`.
    """
    if session_evaluator_id is None:
        if evaluator_id is None:
            raise ValueError(f"Evaluator {evaluator_id} or Session Evaluator {session_evaluator_id} required")
        session_evaluator_id = _resolve_session_evaluator_id(supabase, session_id, evaluator_id)

    update: Dict[str, Any] = {
        "evaluator_form_id": form_id,
        "evaluator_form_view_url": view_url,
        "evaluator_form_edit_url": edit_url,
    }
    _ = (
        supabase.table("session_evaluators")
        .update(update)
        .eq("id", session_evaluator_id)
        .execute()
    )
