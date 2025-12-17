from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, AnyHttpUrl
from typing import Optional
from app.db import get_supabase
from app.services.hooks.make_form_urls_service import save_urls_for_session_evaluator, save_urls_for_session_facility

router = APIRouter()

class SaveEvaluatorFormUrlsBody(BaseModel):
    session_id: int = Field(..., ge=1)
    session_evaluator_id: Optional[int] = Field(None, ge=1)
    evaluator_id: Optional[int] = Field(None, ge=1)
    form_id: str
    view_url: AnyHttpUrl
    edit_url: AnyHttpUrl

@router.post("/save-evaluator-form-urls")
def save_evaluator_form_urls(body: SaveEvaluatorFormUrlsBody, supabase = Depends(get_supabase)):
    try:
        save_urls_for_session_evaluator(
            supabase,
            session_id=body.session_id,
            form_id=body.form_id,
            view_url=str(body.view_url),
            edit_url=str(body.edit_url),
            session_evaluator_id=body.session_evaluator_id,
            evaluator_id=body.evaluator_id,
        )
        return {"ok": True, "session_id": body.session_id, "session_evaluator_id": body.session_evaluator_id, "evaluator_id": body.evaluator_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class SaveFacilityFormUrlsBody(BaseModel):
    session_id: int = Field(..., ge=1)
    form_id: str
    view_url: AnyHttpUrl
    edit_url: AnyHttpUrl

@router.post("/save-facility-form-urls")
def save_facility_form_urls(body: SaveFacilityFormUrlsBody, supabase = Depends(get_supabase)):
    try:
        save_urls_for_session_facility(
            supabase,
            session_id=body.session_id,
            form_id=body.form_id,
            view_url=str(body.view_url),
            edit_url=str(body.edit_url),
        )
        return {"ok": True, "session_id": body.session_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
