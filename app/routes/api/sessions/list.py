from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.db import get_supabase
from app.services.sessions.list_service import fetch_session_list

router = APIRouter()

@router.get("/list")
def get_session_list(
    purpose: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    facility: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    supabase = Depends(get_supabase),
):
    try:
        return fetch_session_list(
            supabase,
            purpose=purpose,
            status=status,
            facility=facility,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
