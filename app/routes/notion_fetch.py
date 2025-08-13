from fastapi import APIRouter, HTTPException, Query
from pydantic import HttpUrl
from notion_client import Client
from typing import List, Dict, Any
import os, re

router = APIRouter()

# Notion property names on the "facility" row
PROP_FACILITY_NAME = "facility name"
PROP_CONTACT       = "担当者名"
PROP_CONTACT_MAIL  = "Mail"
# ---------------------------------------------------

# Notion client
token = os.environ.get("NOTION_TOKEN")
if not token:
    raise RuntimeError("NOTION_TOKEN is not set")
notion = Client(auth=token)

# Regex to match both 32-hex and 36-uuid Notion IDs
UUID_32_OR_36 = re.compile(r"[0-9a-fA-F]{32}|[0-9a-fA-F-]{36}")

def normalize_id(url_or_id: str) -> str:
    """
    Extract 32-hex or 36-uuid from any Notion URL/string and hyphenate to 36 form
    """
    m = UUID_32_OR_36.search(url_or_id)
    if not m:
        raise ValueError("No Notion page ID found. Use Notion → Copy link on the row.")
    raw = m.group(0).replace("-", "").lower()
    return f"{raw[0:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:32]}"

def join_title_plaintext(props: Dict[str, Any], name: str) -> str:
    """
    Join all title fragments' plain_text
    """
    arr = props.get(name, {}).get("title") or []
    return "".join((it.get("plain_text") or "") for it in arr).strip()

def join_rich_text_plaintext(props: Dict[str, Any], name: str) -> str:
    """
    Join all rich_text fragments' plain_text
    """
    arr = props.get(name, {}).get("rich_text") or []
    return "".join((it.get("plain_text") or "") for it in arr).strip()

def extract_title_from_any(props: Dict[str, Any]) -> str:
    """
    Find whichever property is the page's 'title' and return its plain_text
    """
    for v in props.values():
        if v.get("type") == "title":
            arr = v.get("title") or []
            return "".join((it.get("plain_text") or "") for it in arr).strip()
    return ""

def extract_email_from_props(props: Dict[str, Any]) -> str:
    """
    Extract email from Notion properties:
    1) Prefer 'email' type property.
    2) Fallback: scan any rich_text property that looks like an email.
    """
    # 1) proper email type
    for v in props.values():
        if v.get("type") == "email":
            val = v.get("email") or ""
            if val:
                return val.strip()

    # 2) heuristic: any rich_text that looks like an email
    for v in props.values():
        if v.get("type") == "rich_text":
            arr = v.get("rich_text") or []
            txt = "".join((it.get("plain_text") or "") for it in arr)
            if "@" in txt and "." in txt:
                return txt.strip()

    return ""

def collect_page_ids_from_property_value(p: Dict[str, Any]) -> List[str]:
    """
    Minimal extractor (per your schema):
    - relation: relation[].id
    - rollup (array): items with direct 'id'
    - array: items with direct 'id'
    """
    ids: List[str] = []
    t = p.get("type")

    if t == "relation":
        for rel in p.get("relation") or []:
            pid = rel.get("id")
            if isinstance(pid, str):
                ids.append(pid)

    elif t == "rollup":
        roll = p.get("rollup") or {}
        if isinstance(roll, dict) and roll.get("type") == "array":
            for item in roll.get("array") or []:
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    ids.append(item["id"])

    elif t == "array":
        for item in p.get("array") or []:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                ids.append(item["id"])

    return ids

def get_related_page_ids_from_facility(props: Dict[str, Any]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for _, p in props.items():
        for pid in collect_page_ids_from_property_value(p):
            try:
                pid_norm = normalize_id(pid)
            except Exception:
                continue
            if pid_norm not in seen:
                seen.add(pid_norm)
                ordered.append(pid_norm)
    return ordered

@router.get("/notion/facility-info")
def facility_info(url: HttpUrl = Query(..., alias="url")):
    try:
        page_id = normalize_id(str(url))
        page = notion.pages.retrieve(page_id=page_id)
        if page.get("object") != "page":
            raise HTTPException(400, "URL must point to a database item (row)")

        props = page.get("properties", {}) or {}

        # facility name
        facility_name = join_title_plaintext(props, PROP_FACILITY_NAME) or ""

        # contact person
        contact_name  = join_rich_text_plaintext(props, PROP_CONTACT) if PROP_CONTACT in props else ""
        contact_email = join_rich_text_plaintext(props, PROP_CONTACT_MAIL) if PROP_CONTACT_MAIL in props else ""

        # evaluator IDs
        evaluator_ids = get_related_page_ids_from_facility(props)

        evaluators = []
        seen_keys = set()  # dedupe by email or page id

        for eid in evaluator_ids:
            try:
                epage = notion.pages.retrieve(page_id=eid)
                eprops = epage.get("properties", {}) or {}
                ename  = extract_title_from_any(eprops) or ""
                email  = extract_email_from_props(eprops) or ""

                # Prefer dedupe by email; fallback to page id
                dedupe_key = (email or eid).lower()
                if dedupe_key in seen_keys:
                    continue
                seen_keys.add(dedupe_key)

                if ename or email:
                    evaluators.append({"name": ename, "email": email})
            except Exception:
                continue

        return {
            "facility_name": facility_name,
            "contact_person": {"name": contact_name, "email": contact_email},
            "evaluators": evaluators,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Notion fetch failed: {e}")
