from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.db import get_supabase
from app.services.hooks.reminder_mail_service import fetch_due_reminders

router = APIRouter()

@router.get("/reminder-mail")
def get_all_due_reminders(
    as_of_date: Optional[str] = Query(None),
    supabase = Depends(get_supabase)
):
    """
    Returns both evaluator & facility reminder data grouped by session.
    """
    try:
        sessions = fetch_due_reminders(supabase, as_of_date=as_of_date)
        return {
            "ok": True,
            "sessions": sessions,
            "count": len(sessions),
            "as_of_date": as_of_date,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
