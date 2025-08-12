from fastapi import APIRouter, Depends, Query
from app.services.db import get_supabase  # your Supabase client factory

router = APIRouter()

@router.get("/session/list")
def list_sessions(
    purpose: str | None = Query(None),
    status: str | None = Query(None),
    facility: str | None = Query(None),
    supabase = Depends(get_supabase),
):
    q = supabase.table("session_list").select(
        "id, facility_name, notion_url, purpose, status, confirmed_date"
    )
    if purpose:  q = q.eq("purpose", purpose)
    if status:   q = q.eq("status", status)
    if facility: q = q.ilike("facility_name", f"%{facility}%")
    resp = q.order("created_at", desc=True).execute()
    return resp.data
