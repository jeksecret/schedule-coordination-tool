from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from app.db import get_supabase
from app.services.sessions.list_service import fetch_session_list

router = APIRouter()

class SessionListQuery(BaseModel):
    purpose: Optional[str] = None
    status: Optional[str] = None
    facility: Optional[str] = None
    page: int = Field(1, ge=1, description="1-based page number")
    page_size: int = Field(10, ge=1, le=100, description="Rows per page (max 100)")

@router.get("/list")
def get_session_list(q: SessionListQuery = Depends(), supabase = Depends(get_supabase)):
    try:
        return fetch_session_list(
            supabase,
            purpose=q.purpose,
            status=q.status,
            facility=q.facility,
            page=q.page,
            page_size=q.page_size,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
