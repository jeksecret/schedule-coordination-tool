from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl, field_validator
from typing import List
from datetime import date
from app.db import get_supabase
from app.services.sessions.create_service import create_session_with_notion

router = APIRouter()

class CandidateSlotIn(BaseModel):
    slot_date: date
    slot_label: str

    @field_validator("slot_label")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("候補日程（時刻/備考）は空にできません。")
        return v.strip()

class CreateSessionBody(BaseModel):
    notion_url: HttpUrl
    purpose: str
    response_deadline: date
    presentation_date: date
    candidate_slots: List[CandidateSlotIn]

    @field_validator("candidate_slots", mode="after")
    @classmethod
    def _normalize_candidates(cls, v: List[CandidateSlotIn]) -> List[CandidateSlotIn]:
        cleaned = [c for c in v if c and c.slot_date and (c.slot_label or "").strip()]
        if not cleaned:
            raise ValueError("候補日程を1件以上指定してください。")
        return cleaned

@router.post("/create")
def create_session(body: CreateSessionBody, supabase = Depends(get_supabase)):
    try:
        session_id = create_session_with_notion(
            supabase,
            notion_url=body.notion_url,
            purpose=body.purpose,
            response_deadline=body.response_deadline,
            presentation_date=body.presentation_date,
            candidate_slots=[c.model_dump() for c in body.candidate_slots],
        )
        return {"session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
