# app/routes/meta.py
from fastapi import APIRouter, Depends, HTTPException
from app.services.db import get_supabase

router = APIRouter()

@router.get("/meta/enums")
def get_enums(supabase = Depends(get_supabase)):
    try:
        p = supabase.rpc("purpose_enum_values").execute().data or []
        s = supabase.rpc("status_enum_values").execute().data or []
        return {"purpose": p, "status": s}
    except Exception as e:
        raise HTTPException(500, str(e))
