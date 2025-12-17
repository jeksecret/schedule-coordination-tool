import { PURPOSE_OPTIONS, STATUS_OPTIONS } from "./constants";

export function toFilterOptions(values) {
  return [
    { value: "", label: "すべて" },
    ...values.map((value) => ({ value, label: value })),
  ];
}

export function resolvePurposeOptions(payload) {
  const incoming = Array.isArray(payload?.purpose) ? payload.purpose : null;
  return incoming && incoming.length ? incoming : PURPOSE_OPTIONS;
}

export function resolveStatusOptions(payload) {
  const incoming = Array.isArray(payload?.status) ? payload.status : null;
  return incoming && incoming.length ? incoming : STATUS_OPTIONS;
}

export function mapSessionListItems(items = []) {
  return (items || []).map((item) => ({
    id: item.id,
    facilityName: item.facility_name,
    purpose: item.purpose,
    status: item.status,
    confirmedDate: item.confirmed_date ? String(item.confirmed_date) : "－",
    notionUrl: item.notion_url,
    progress: {
      done: item.answered ?? 0,
      total: item.total_evaluators ?? 0,
    },
    hasClientConfirmation: Boolean(item.confirmed_date),
  }));
}

export function resolveTotal(out, mappedItems) {
  if (typeof out?.total === "number") return out.total;
  return mappedItems.length;
}
