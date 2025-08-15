from fastapi import APIRouter, Depends, HTTPException, Path
from app.db import get_supabase
from app.services.sessions.confirmation_summary_service import fetch_confirmation_summary

router = APIRouter()

@router.get("/{session_id}/confirmation-summary")
def get_confirmation_summary(
    session_id: int = Path(..., ge=1),
    supabase = Depends(get_supabase),
):
    try:
        row = fetch_confirmation_summary(supabase, session_id=session_id)
        if not row:
            raise HTTPException(status_code=404, detail="No data found.")
        return row
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
