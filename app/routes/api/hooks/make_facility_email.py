from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Any, Dict
from http import HTTPStatus
import json, os
from app.db import get_supabase
from app.services.hooks.make_facility_email_service import (
    build_make_payload, post_to_make_webhook
)

router = APIRouter()

class GenerateFacilityEmailBody(BaseModel):
    session_id: int = Field(..., ge=1)
    candidate_slot_ids: List[int] = Field(default_factory=list)

@router.post("/generate-facility-email")
def generate_facility_email(body: GenerateFacilityEmailBody, supabase = Depends(get_supabase)):
    try:
        payload = build_make_payload(
            supabase,
            session_id=body.session_id,
            candidate_slot_ids=body.candidate_slot_ids,
        )

        timeout_sec = int(os.getenv("MAKE_HTTP_TIMEOUT_SECONDS", "120"))
        status, raw = post_to_make_webhook(payload, timeout_sec=timeout_sec)

        try:
            make_json: Dict[str, Any] = json.loads(raw) if raw else {}
        except Exception:
            make_json = {"raw": raw} if raw else {}

        if HTTPStatus.OK <= status < HTTPStatus.MULTIPLE_CHOICES:
            gmail_url = make_json.get("gmail_draft_url")
            return {
                "ok": True,
                "session_id": body.session_id,
                "make_status": status,
                **({"gmail_draft_url": gmail_url} if gmail_url else {}),
            }

        raise HTTPException(status_code=HTTPStatus.BAD_GATEWAY, detail=f"Make webhook returned {status}")

    except TimeoutError as te:
        raise HTTPException(status_code=HTTPStatus.GATEWAY_TIMEOUT, detail=str(te))
    except Exception as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))
