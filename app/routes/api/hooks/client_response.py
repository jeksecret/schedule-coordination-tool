from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
from app.db import get_supabase
from app.services.hooks.client_response_service import insert_client_response
from app.services.hooks.client_response_notify_service import post_to_make_webhook
import json

router = APIRouter()

class ClientResponsePayload(BaseModel):
    session_id: int = Field(..., ge=1)
    selected_candidate_slot_id: Optional[int] = Field(default=None, ge=1)
    note: Optional[str] = None

@router.post("/save-client-response")
def save_client_response(
    payload: ClientResponsePayload,
    background_tasks: BackgroundTasks,
    supabase = Depends(get_supabase),
):
    try:
        result = insert_client_response(
            supabase,
            session_id=payload.session_id,
            selected_candidate_slot_id=payload.selected_candidate_slot_id,
            note=payload.note,
        )

        background_tasks.add_task(
            post_to_make_webhook,
            result.get("client_response_payload") or {}
        )

        return result

    except ValueError as ve:
        msg = str(ve)
        if "already been submitted" in msg:
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    except Exception as e:
        if e.args and isinstance(e.args[0], dict):
            raise HTTPException(status_code=400, detail=json.dumps(e.args[0]))
        raise HTTPException(status_code=400, detail=str(e))
