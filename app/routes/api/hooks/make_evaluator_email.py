from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.db import get_supabase
from app.services.hooks.make_evaluator_email_service import (
    build_make_payload, post_to_make_webhook, mark_session_status
)

router = APIRouter()

class GenerateEmailBody(BaseModel):
    session_id: int = Field(..., ge=1)

@router.post("/generate-evaluator-email")
def generate_email(body: GenerateEmailBody, supabase = Depends(get_supabase)):
    """
    Build payload and POST to Make webhook.
    """
    SET_STATUS = "評価者待ち"
    try:
        payload = build_make_payload(supabase, body.session_id)
        status = post_to_make_webhook(payload)
        if 200 <= status < 300:
            mark_session_status(supabase, body.session_id, SET_STATUS)
            return {"ok": True, "session_id": body.session_id, "make_status": status}
        raise HTTPException(status_code=502, detail=f"Make webhook returned {status}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
