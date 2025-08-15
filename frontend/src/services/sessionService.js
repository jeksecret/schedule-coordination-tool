export async function fetchEnums(signal) {
  const res = await fetch("/api/meta/enums", {
    credentials: "include",
    signal,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchSessionList(params, signal) {
  const { purpose, status, facility, page, page_size } = params;
  const qs = new URLSearchParams();
  if (purpose) qs.set("purpose", purpose);
  if (status) qs.set("status", status);
  if (facility) qs.set("facility", facility);
  qs.set("page", String(page));
  qs.set("page_size", String(page_size));

  const res = await fetch(`/api/sessions/list?${qs.toString()}`, {
    credentials: "include",
    signal,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchFacilityInfo(notionUrl, signal) {
  const res = await fetch(
    `/api/notion/facility-info?url=${encodeURIComponent(notionUrl)}`,
    {
      credentials: "include",
      signal,
    }
  );
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
