from datetime import date
from typing import Any, Dict, List, Optional
import re

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", re.IGNORECASE)

def _extract_emails(text: str) -> List[str]:
    """Extract all emails from arbitrary text (handles commas/newlines/etc)."""
    if not text:
        return []
    norm = (
        text.replace("\r\n", " ")
            .replace("\n", " ")
            .replace("、", " ")
            .replace(";", " ")
            .replace(",", " ")
    )
    return [m.strip() for m in _EMAIL_RE.findall(norm)]

def fetch_due_reminders(supabase, as_of_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch evaluator & facility reminders grouped by session.

    Evaluator:
      - sessions.response_deadline == today
      - session_evaluators.answered_at IS NULL
      - evaluator_form_view_url IS NOT NULL

    Facility:
      - sessions.presentation_date == today
      - client_responses.answered_at IS NULL OR no record
      - facility_form_view_url IS NOT NULL
    """
    today = as_of_date or date.today().isoformat()

    rows = (
        supabase.table("sessions")
        .select(
            "id, purpose, response_deadline, presentation_date, "
            "facility: facilities(name, contact_name, contact_email), "
            "facility_form_view_url, "
            "session_evaluators(id, answered_at, evaluator_id, "
            "evaluator_form_view_url, "
            "evaluator: evaluators(name, email)), "
            "client_responses(id, answered_at)"
        )
        .or_(f"response_deadline.eq.{today},presentation_date.eq.{today}")
        .execute()
    ).data or []

    sessions_grouped: List[Dict[str, Any]] = []

    for s in rows:
        facility = s.get("facility") or {}
        se_list = s.get("session_evaluators") or []

        # Normalize client_responses
        cr_raw = s.get("client_responses")

        if cr_raw is None:
            cr_list = []
        elif isinstance(cr_raw, list):
            cr_list = cr_raw
        else:
            cr_list = [cr_raw]

        evaluators_section = []
        facility_section = []

        # Evaluator reminders
        if s.get("response_deadline") == today:
            for se in se_list:
                if se.get("answered_at") is None and se.get("evaluator_form_view_url"):
                    ev = se.get("evaluator") or {}
                    emails = _extract_emails(ev.get("email") or "")
                    evaluators_section.append({
                        "evaluator_name": ev.get("name"),
                        "evaluator_email": emails,
                        "form_view_url": se.get("evaluator_form_view_url"),
                    })

        # Facility reminders
        if s.get("presentation_date") == today:
            form_view_url = s.get("facility_form_view_url")

            # No response → send reminder
            if len(cr_list) == 0:
                if form_view_url:
                    recipients = _extract_emails(facility.get("contact_email") or "")
                    facility_section.append({
                        "contact_name": facility.get("contact_name"),
                        "contact_emails": recipients,
                        "form_view_url": form_view_url,
                    })

            else:
                # Check each response
                has_unanswered = any(cr.get("answered_at") is None for cr in cr_list)

                if has_unanswered and form_view_url:
                    recipients = _extract_emails(facility.get("contact_email") or "")
                    facility_section.append({
                        "contact_name": facility.get("contact_name"),
                        "contact_emails": recipients,
                        "form_view_url": form_view_url,
                    })

        if evaluators_section or facility_section:
            sessions_grouped.append({
                "session_id": s["id"],
                "purpose": s.get("purpose"),
                "response_deadline": s.get("response_deadline"),
                "presentation_date": s.get("presentation_date"),
                "facility_name": facility.get("name"),
                "facility": facility_section,
                "evaluators": evaluators_section,
            })

    return sessions_grouped
