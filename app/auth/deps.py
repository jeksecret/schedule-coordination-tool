import os
from fastapi import Header, HTTPException
from jose import jwt, JWTError
from app.security.domain_policy import is_allowed_domain

AUD = "authenticated"

SUPABASE_JWT_SECRET = None

def _get_jwt_secret() -> str:
    global SUPABASE_JWT_SECRET
    if SUPABASE_JWT_SECRET is None:
        SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET") or ""
    if not SUPABASE_JWT_SECRET:
        raise HTTPException(status_code=503, detail="Server misconfigured: SUPABASE_JWT_SECRET is not set")
    return SUPABASE_JWT_SECRET

def require_allowed_user(authorization: str = Header(None)):
    """
    HS256-only validator for Supabase access tokens.
    - Verifies signature with SUPABASE_JWT_SECRET
    - Enforces aud='authenticated'
    - Blocks emails outside allowed domains
    """
    # Require Authorization: Bearer <token>
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header must be Bearer")

    token = authorization.split(" ", 1)[1]

    # Ensure HS256 token
    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token header (cannot parse)")

    alg = (header.get("alg") or "").upper()
    if alg != "HS256":
        raise HTTPException(status_code=401, detail=f"Unsupported JWT alg for this server: {alg}")

    # Verify & decode
    secret = _get_jwt_secret()
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience=AUD,
        )
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"JWT decode failed (HS256): {e}")

    # Domain allow-list
    email = (claims.get("email") or "").lower()
    if not is_allowed_domain(email):
        raise HTTPException(status_code=403, detail="Forbidden domain")

    return claims
