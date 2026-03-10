import os
from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from app.security.domain_policy import is_allowed_domain
from app.services.hooks.auth.before_user_created_service import verify_webhook_signature

router = APIRouter()

WEBHOOK_SECRET = (os.getenv("SUPABASE_AUTH_HOOK_SECRET") or "").strip()
REQUIRE_SIG = (os.getenv("SUPABASE_AUTH_HOOK_REQUIRE_SIGNATURE", "false").strip().lower() == "true")

@router.post("/before-user-created")
async def before_user_created(
    request: Request,
    x_supabase_signature: str = Header(default="", alias="X-Supabase-Signature"),
    x_supabase_timestamp: str = Header(default="", alias="X-Supabase-Timestamp")
):
    body = await request.body()

    # signature verification
    if REQUIRE_SIG:
        verify_webhook_signature(
            body=body,
            signature_header=x_supabase_signature,
            timestamp_header=x_supabase_timestamp,
            secret=WEBHOOK_SECRET
        )

    payload = await request.json()
    email = (
        payload.get("user", {}).get("email")
        or payload.get("record", {}).get("email")
        or ""
    )

    # reject if domain not allowed
    if not is_allowed_domain(email):
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": "Forbidden domain",
                    "http_code": 400
                }
            }
        )

    # allow user creation
    return JSONResponse(status_code=200, content={})
