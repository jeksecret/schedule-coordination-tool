from typing import Dict, Any, List
from pydantic import HttpUrl
from notion_client import Client
import os, re

# Notion property names on the "facility" row
PROP_FACILITY_NAME = "facility name"
PROP_CONTACT = "担当者名"
PROP_CONTACT_MAIL = "Mail"

# Notion client
_token = os.environ.get("NOTION_API_TOKEN")
if not _token:
    raise RuntimeError("NOTION_API_TOKEN is not set")
_notion = Client(auth=_token)

# Regex to match both 32-hex and 36-uuid Notion IDs
_UUID_32_OR_36 = re.compile(r"[0-9a-fA-F]{32}|[0-9a-fA-F-]{36}")

def normalize_id(url_or_id: str) -> str:
    m = _UUID_32_OR_36.search(url_or_id)
    if not m:
        raise ValueError("No Notion page ID found. Use Notion → Copy link on the row.")
    raw = m.group(0).replace("-", "").lower()
    if len(raw) != 32:
        raise ValueError(f"Notion page ID must be 32 hex digits after removing dashes, got {len(raw)}: {raw!r}")
    return f"{raw[0:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:32]}"

def _join_title_plaintext(props: Dict[str, Any], name: str) -> str:
    arr = props.get(name, {}).get("title") or []
    return "".join((it.get("plain_text") or "") for it in arr).strip()

def _join_rich_text_plaintext(props: Dict[str, Any], name: str) -> str:
    arr = props.get(name, {}).get("rich_text") or []
    return "".join((it.get("plain_text") or "") for it in arr).strip()

def _extract_title_from_any(props: Dict[str, Any]) -> str:
    for v in props.values():
        if v.get("type") == "title":
            arr = v.get("title") or []
            return "".join((it.get("plain_text") or "") for it in arr).strip()
    return ""

def _extract_email_from_props(props: Dict[str, Any]) -> str:
    # 1) prefer 'email' type
    for v in props.values():
        if v.get("type") == "email":
            val = v.get("email") or ""
            if val:
                return val.strip()
    # 2) lightweight heuristic from rich_text
    for v in props.values():
        if v.get("type") == "rich_text":
            arr = v.get("rich_text") or []
            txt = "".join((it.get("plain_text") or "") for it in arr)
            if "@" in txt and "." in txt:
                return txt.strip()
    return ""

def _collect_ids_from_property(p: Dict[str, Any]) -> List[str]:
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

def _related_page_ids(props: Dict[str, Any]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for _, p in props.items():
        for pid in _collect_ids_from_property(p):
            try:
                pid_norm = normalize_id(pid)
            except Exception:
                continue
            if pid_norm not in seen:
                seen.add(pid_norm)
                ordered.append(pid_norm)
    return ordered

def fetch_facility_info(notion_url: HttpUrl) -> Dict[str, Any]:
    """Return { facility_name, contact_person: {name,email}, evaluators: [{name,email}...] }"""
    page_id = normalize_id(str(notion_url))
    page = _notion.pages.retrieve(page_id=page_id)
    if page.get("object") != "page":
        raise ValueError("URL must point to a database item (row)")
    props = page.get("properties", {}) or {}

    facility_name = _join_title_plaintext(props, PROP_FACILITY_NAME) or ""
    contact_name = _join_rich_text_plaintext(props, PROP_CONTACT) if PROP_CONTACT in props else ""
    contact_email = _join_rich_text_plaintext(props, PROP_CONTACT_MAIL) if PROP_CONTACT_MAIL in props else ""

    evaluator_ids = _related_page_ids(props)
    evaluators = []
    seen = set()
    for eid in evaluator_ids:
        try:
            epage = _notion.pages.retrieve(page_id=eid)
            eprops = epage.get("properties", {}) or {}
            ename  = _extract_title_from_any(eprops) or ""
            email  = _extract_email_from_props(eprops) or ""
            dedupe_key = (email or eid).lower()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            if ename or email:
                evaluators.append({"name": ename, "email": email})
        except Exception:
            continue

    return {
        "notion_page_id": page_id,
        "facility_name": facility_name,
        "contact_person": {"name": contact_name, "email": contact_email},
        "evaluators": evaluators,
    }
