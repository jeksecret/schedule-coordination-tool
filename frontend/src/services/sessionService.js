import { API_BASE } from "../config";
import { fetchWithAuthJson } from "../lib/fetchWithAuth";

export async function fetchEnums(signal) {
  return fetchWithAuthJson(`${API_BASE}/api/meta/enums`, {
    method: "GET",
    signal,
  });
}

export async function fetchSessionList(params, signal) {
  const { purpose, status, facility, page, page_size } = params;
  const qs = new URLSearchParams();
  if (purpose) qs.set("purpose", purpose);
  if (status) qs.set("status", status);
  if (facility) qs.set("facility", facility);
  qs.set("page", String(page));
  qs.set("page_size", String(page_size));

  return fetchWithAuthJson(`${API_BASE}/api/sessions/list?${qs.toString()}`, {
    method: "GET",
    signal,
  });
}

export async function fetchFacilityInfo(notionUrl, signal) {
  return fetchWithAuthJson(
    `${API_BASE}/api/notion/facility-info?url=${encodeURIComponent(notionUrl)}`,
    {
      method: "GET",
      signal,
    }
  );
}

export async function createSession(payload, signal) {
  return fetchWithAuthJson(`${API_BASE}/api/sessions/create`, {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

export async function generateEvaluatorEmail(sessionId, signal) {
  return fetchWithAuthJson(`${API_BASE}/api/hooks/generate-evaluator-email`, {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
    signal,
  });
}

export async function fetchSessionStatus(sessionId, signal) {
  return fetchWithAuthJson(`${API_BASE}/api/sessions/${sessionId}/status`, {
    method: "GET",
    signal,
  });
}

export async function updateSession(sessionId, payload, signal) {
  return fetchWithAuthJson(`${API_BASE}/api/sessions/${sessionId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
    signal,
  });
}

export async function updateEvaluatorResponses(
  sessionId,
  evaluatorId,
  payload,
  signal
) {
  return fetchWithAuthJson(
    `${API_BASE}/api/sessions/${sessionId}/evaluators/${evaluatorId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
      signal,
    }
  );
}

export async function checkSlotEveryoneOk(sessionId, slotId, signal) {
  return fetchWithAuthJson(
    `${API_BASE}/api/sessions/${sessionId}/slots/${slotId}/check`,
    {
      method: "GET",
      signal,
    }
  );
}

export async function generateFacilityEmail(
  sessionId,
  candidateSlotIds,
  signal
) {
  return fetchWithAuthJson(`${API_BASE}/api/hooks/generate-facility-email`, {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      candidate_slot_ids: candidateSlotIds,
    }),
    signal,
  });
}

export function extractGmailDraftUrl(res) {
  if (!res) return "";
  if (typeof res.gmail_draft_url === "string" && res.gmail_draft_url)
    return res.gmail_draft_url;
  if (typeof res.raw === "string" && res.raw.includes("mail.google.com")) {
    const m = res.raw.match(/https?:\/\/mail\.google\.com\/[^\s"]+/);
    return m ? m[0] : "";
  }
  return "";
}

export async function fetchConfirmationSummary(sessionId, signal) {
  return fetchWithAuthJson(
    `${API_BASE}/api/sessions/${sessionId}/confirmation-summary`,
    {
      method: "GET",
      signal,
    }
  );
}
