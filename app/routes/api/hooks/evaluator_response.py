from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from app.db import get_supabase
from app.services.hooks.evaluator_response_service import insert_evaluator_response

router = APIRouter()

SYMBOL_TO_DB = {"○": "O", "△": "M", "x": "X"}
ALLOWED = {"O", "M", "X"}

class EvaluatorResponsePayload(BaseModel):
    token: str = Field(..., min_length=8)
    answers: Dict[int, Optional[str]] = Field(default_factory=dict)
    note: Optional[str] = None

    @field_validator("answers", mode="before")
    @classmethod
    def normalize_answers(cls, v: Any) -> Dict[int, Optional[str]]:
        out: Dict[int, Optional[str]] = {}
        if not isinstance(v, dict):
            return out
        for k, val in v.items():
            try:
                sid = int(k)
            except Exception:
                continue
            if val is None or str(val).strip() == "":
                continue
            s = str(val).strip()
            token = SYMBOL_TO_DB.get(s, s.upper())
            if token in ALLOWED:
                out[sid] = token
        return out

@router.post("/save-evaluator-response")
def save_evaluator_response(payload: EvaluatorResponsePayload, supabase = Depends(get_supabase)):
    try:
        return insert_evaluator_response(
            supabase=supabase,
            token=payload.token,
            answers=payload.answers,
            note=payload.note,
        )
    except ValueError as ve:
        msg = str(ve)
        if msg == "Invalid token":
            raise HTTPException(status_code=401, detail=msg)
        if "already submitted" in msg:
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
