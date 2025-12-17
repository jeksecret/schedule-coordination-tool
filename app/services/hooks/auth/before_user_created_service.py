import base64
import hmac
from hashlib import sha256
from typing import Tuple
from fastapi import HTTPException

ALLOWED_DOMAINS = ("smartworx.co.jp", "nabepero.co.jp", "cio-sw.com")

def is_allowed_domain(email: str) -> bool:
    """Return True if the email ends with one of the allowed domains."""
    e = (email or "").lower()
    return any(e.endswith(f"@{d}") for d in ALLOWED_DOMAINS)

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
    if not secret_value:
        return b""

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

def _match(body: bytes, timestamp: str, sig: bytes, secret_ui: str) -> bool:
    """
    Accept multiple HMAC bases & secret interpretations to be resilient:
    A) HMAC_SHA256(body) with base64-decoded secret
    B) HMAC_SHA256(timestamp + '.' + body) with base64-decoded secret
    C) HMAC_SHA256(body) with raw secret bytes
    D) HMAC_SHA256(timestamp + '.' + body) with raw secret bytes
    """
    dec = _b64_secret_bytes(secret_ui)
    if dec and hmac.compare_digest(hmac.new(dec, body, sha256).digest(), sig):
        return True
    if dec and timestamp and hmac.compare_digest(
        hmac.new(dec, timestamp.encode() + b"." + body, sha256).digest(), sig
    ):
        return True

    raw = secret_ui.encode()
    if raw and hmac.compare_digest(hmac.new(raw, body, sha256).digest(), sig):
        return True
    if raw and timestamp and hmac.compare_digest(
        hmac.new(raw, timestamp.encode() + b"." + body, sha256).digest(), sig
    ):
        return True

    return False

def verify_webhook_signature_or_raise(
    body: bytes,
    signature_header: str,
    timestamp_header: str,
    secret: str,
    require_signature: bool,
):
    """
    Verify signature if require_signature=True.
    """
    if not require_signature:
        return

    ver, sig = parse_signature(signature_header)
    if ver != "v1" or not sig:
        raise HTTPException(status_code=401, detail="Invalid webhook signature header")
    if not _match(body, timestamp_header, sig, secret):
        raise HTTPException(status_code=401, detail="Webhook signature mismatch")
