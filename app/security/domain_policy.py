import os

DEFAULT_DOMAINS = ("smartworx.co.jp", "nabepero.co.jp", "cio-sw.com")

def get_allowed_domains() -> tuple[str, ...]:
    raw = os.getenv("ALLOWED_DOMAINS")
    if raw:
        return tuple(d.strip() for d in raw.split(",") if d.strip())
    return DEFAULT_DOMAINS

def is_allowed_domain(email: str) -> bool:
    email = (email or "").lower()
    return any(email.endswith(f"@{d}") for d in get_allowed_domains())
