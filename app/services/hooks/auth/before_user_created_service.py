import base64
import hmac
from hashlib import sha256
from typing import Tuple
from fastapi import HTTPException

def parse_signature(header_value: str) -> Tuple[str, bytes]:
    """
    Supabase typically sends the signature header value as 'v1,<base64sig>' or 'v1=<base64sig>'.
    """
    if not header_value:
        return "", b""
    if "," in header_value:
        v, b64 = header_value.split(",", 1)
    elif "=" in header_value:
        v, b64 = header_value.split("=", 1)
    else:
        return "", b""
    try:
        return v.strip(), base64.b64decode(b64.strip())
    except Exception:
        return "", b""

def _b64_secret_bytes(secret_value: str) -> bytes:
    """
    Accept Supabase UI secrets in different formats:
    - v1,whsec_<base64>
    - v1_whsec_<base64>
    - whsec_<base64>
    - raw base64
    """
    raw = secret_value.strip()
    if raw.startswith("v1,whsec_"):
        raw = raw[len("v1,whsec_") :]
    elif raw.startswith("v1_whsec_"):
        raw = raw[len("v1_whsec_") :]
    elif raw.startswith("whsec_"):
        raw = raw[len("whsec_") :]
    try:
        return base64.b64decode(raw)
    except Exception:
        return b""

def verify_webhook_signature(
    body: bytes,
    signature_header: str,
    timestamp_header: str,
    secret: str
):
    """
    Verify signature if require_signature=True.
    """
    ver, sig = parse_signature(signature_header)
    if ver != "v1" or not sig:
        raise HTTPException(status_code=401, detail="Invalid webhook signature header")

    secret_bytes = _b64_secret_bytes(secret)
    if not secret_bytes:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    # compute expected digest
    expected = hmac.new(secret_bytes, timestamp_header.encode() + b"." + body, sha256).digest()

    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=401, detail="Webhook signature mismatch")
