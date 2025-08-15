import os
from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from app.services.hooks.auth.before_user_created_service import (
    is_allowed_domain,
    verify_webhook_signature_or_raise,
)

router = APIRouter()

WEBHOOK_SECRET = (os.environ.get("SUPABASE_AUTH_HOOK_SECRET") or "").strip()
REQUIRE_SIG = (os.environ.get("SUPABASE_AUTH_HOOK_REQUIRE_SIGNATURE", "true").lower() == "true")

@router.post("/before-user-created")
async def before_user_created(
    request: Request,
    webhook_signature: str = Header(default=""),
    webhook_timestamp: str = Header(default=""),
):
    body = await request.body()

    verify_webhook_signature_or_raise(
        body=body,
        signature_header=webhook_signature,
        timestamp_header=webhook_timestamp,
        secret=WEBHOOK_SECRET,
        require_signature=REQUIRE_SIG,
    )

    payload = await request.json()
    email = (
        payload.get("record", {}).get("email")
        or payload.get("user", {}).get("email")
        or payload.get("email")
        or ""
    )

    if not is_allowed_domain(email):
        return JSONResponse(status_code=400, content={"message": "Forbidden domain"})

    return JSONResponse(status_code=200, content={})
