from fastapi import APIRouter, HTTPException, Query
from pydantic import HttpUrl
from app.services.notion.facility_info_service import fetch_facility_info

router = APIRouter()

@router.get("/facility-info")
def facility_info(url: HttpUrl = Query(..., alias="url")):
    try:
        return fetch_facility_info(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
