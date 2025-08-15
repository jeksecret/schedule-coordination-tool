import os
from fastapi import Header, HTTPException
from jose import jwt, JWTError

AUD = "authenticated"

_SUPABASE_JWT_SECRET = None
_ALLOWED_DOMAINS = None

def _get_jwt_secret() -> str:
    global _SUPABASE_JWT_SECRET
    if _SUPABASE_JWT_SECRET is None:
        _SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET") or ""
    if not _SUPABASE_JWT_SECRET:
        raise HTTPException(status_code=503, detail="Server misconfigured: SUPABASE_JWT_SECRET is not set")
    return _SUPABASE_JWT_SECRET

def _get_allowed_domains() -> tuple[str, ...]:
    global _ALLOWED_DOMAINS
    if _ALLOWED_DOMAINS is None:
        raw = os.getenv("ALLOWED_DOMAINS")
        if raw:
            _ALLOWED_DOMAINS = tuple(d.strip() for d in raw.split(",") if d.strip())
        else:
            _ALLOWED_DOMAINS = ("smartworx.co.jp", "nabepero.co.jp")
    return _ALLOWED_DOMAINS

def _is_allowed_domain(email: str) -> bool:
    email = (email or "").lower()
    return any(email.endswith(f"@{d}") for d in _get_allowed_domains())

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
    if not _is_allowed_domain(email):
        raise HTTPException(status_code=403, detail="Forbidden domain")

    return claims
