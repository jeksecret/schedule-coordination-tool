from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.services.db import get_supabase

router = APIRouter()

@router.get("/session/list")
def list_sessions(
    purpose: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    facility: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    supabase = Depends(get_supabase),
):
    try:
        offset = (page - 1) * page_size
        end = offset + page_size - 1

        q = (
            supabase
            .table("session_list")
            .select(
                "id, facility_name, purpose, status, confirmed_date, notion_url, updated_at",
                count="exact"
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
        # exposes count on the response
        total = getattr(res, "count", None)
        if total is None:
            total = len(items)

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
