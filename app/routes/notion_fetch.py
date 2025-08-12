# app/routes/notion_fetch.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import HttpUrl
from notion_client import Client
import os, re

router = APIRouter()

# --- Notion property names ---
PROP_FACILITY_NAME = "facility name"
PROP_CONTACT       = "担当者名"
PROP_CONTACT_MAIL  = "Mail"
# ------------------------------

# Notion client
token = os.environ.get("NOTION_TOKEN")
if not token:
    raise RuntimeError("NOTION_TOKEN is not set")
notion = Client(auth=token)

def normalize_id(url: str) -> str:
    """Extract 32-hex or 36-uuid from any Notion URL and hyphenate."""
    m = re.search(r"[0-9a-fA-F]{32}|[0-9a-fA-F-]{36}", url)
    if not m:
        raise ValueError("No Notion ID found in URL. Use Notion → Copy link on the row.")
    raw = m.group(0).replace("-", "").lower()
    return f"{raw[0:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:32]}"

def join_title_plaintext(props, name: str) -> str:
    """Join all title fragments' plain_text."""
    arr = props.get(name, {}).get("title") or []
    return "".join((it.get("plain_text") or "") for it in arr).strip()

def join_rich_text_plaintext(props, name: str) -> str:
    """Join all rich_text fragments' plain_text."""
    arr = props.get(name, {}).get("rich_text") or []
    return "".join((it.get("plain_text") or "") for it in arr).strip()

@router.get("/notion/facility-info")
def facility_info(url: HttpUrl = Query(..., alias="url")):
    try:
        page_id = normalize_id(str(url))
        page = notion.pages.retrieve(page_id=page_id)
        if page.get("object") != "page":
            raise HTTPException(400, "URL must point to a database item (row)")

        props = page.get("properties", {})

        # facility name (Title → plain_text)
        facility_name = (join_title_plaintext(props, PROP_FACILITY_NAME) or "")

        # contact person:
        # - name from 担当者名 (rich_text → plain_text)
        # - email from Mail (rich_text → plain_text)
        contact_name  = join_rich_text_plaintext(props, PROP_CONTACT) if PROP_CONTACT in props else ""
        contact_email = join_rich_text_plaintext(props, PROP_CONTACT_MAIL) if PROP_CONTACT_MAIL in props else ""

        return {
            "facility_name": facility_name,
            "contact_person": {
                "name": contact_name,
                "email": contact_email,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Notion fetch failed: {e}")
