from typing import Dict, Any, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Path, Body
from pydantic import BaseModel, Field, field_validator
from app.db import get_supabase
from app.services.sessions.status_service import (
    fetch_session_status,
    update_evaluator_responses,
    update_session,
    check_slot_everyone_ok,
)

router = APIRouter()
class SessionStatusParams(BaseModel):
    session_id: int = Field(..., ge=1)

def _status_params(session_id: int = Path(..., ge=1)) -> SessionStatusParams:
    return SessionStatusParams(session_id=session_id)

@router.get("/{session_id}/status")
def get_session_status(
    q: SessionStatusParams = Depends(_status_params),
    supabase = Depends(get_supabase),
):
    """
    Fetch data for session status.
    """
    try:
        return fetch_session_status(supabase, q.session_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
class UpdateSessionPayload(BaseModel):
    purpose: Optional[str] = Field(None)
    response_deadline: Optional[date] = Field(None)
    presentation_date: Optional[date] = Field(None)

    @field_validator("purpose")
    @classmethod
    def _validate_purpose(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = v.strip()
        if not s:
            return None
        allowed = {"訪問調査", "聞き取り", "場面観察", "FB", "その他"}
        if s not in allowed:
            raise ValueError("Invalid purpose")
        return s

@router.patch("/{session_id}")
def patch_session(
    session_id: int = Path(..., ge=1),
    payload: UpdateSessionPayload = Body(...),
    supabase = Depends(get_supabase),
):
    """
    Update top-level session header fields:
      - purpose
      - response_deadline
      - presentation_date
    """
    try:
        return update_session(
            supabase=supabase,
            session_id=session_id,
            purpose=payload.purpose,
            response_deadline=payload.response_deadline,
            presentation_date=payload.presentation_date,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
class UpdateEvaluatorPayload(BaseModel):
    """
    Admin edit payload for a single evaluator in a session.
    """
    note: Optional[str] = None
    answers: Dict[int, Optional[str]] = Field(default_factory=dict)

    @field_validator("answers", mode="before")
    @classmethod
    def _normalize_answers(cls, v: Dict[Any, Any]) -> Dict[int, Optional[str]]:
        out: Dict[int, Optional[str]] = {}
        if not isinstance(v, dict):
            return out
        for k, val in v.items():
            try:
                sid = int(k)
            except Exception:
                continue
            if val is None:
                out[sid] = None
            else:
                sval = str(val).strip()
                out[sid] = sval if sval else ""
        return out

@router.patch("/{session_id}/evaluators/{evaluator_id}")
def patch_evaluator_responses(
    session_id: int = Path(..., ge=1),
    evaluator_id: int = Path(..., ge=1),
    payload: UpdateEvaluatorPayload = Body(...),
    supabase = Depends(get_supabase),
):
    """
    Admin update for a single evaluator's answers + note.
    """
    try:
        return update_evaluator_responses(
            supabase=supabase,
            session_id=session_id,
            evaluator_id=evaluator_id,
            note=payload.note,
            answers=payload.answers,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{session_id}/slots/{slot_id}/check")
def check_everyone_ok(
    session_id: int = Path(..., ge=1),
    slot_id: int = Path(..., ge=1),
    supabase = Depends(get_supabase),
):
    try:
        return check_slot_everyone_ok(supabase, session_id, slot_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
