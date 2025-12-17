import { MSG_DATE_REQUIRED, MSG_DATE_FORMAT_INVALID } from "./messages";

const DAYS_LABEL = ["日", "月", "火", "水", "木", "金", "土"];

export function isYmd(value) {
  return /^\d{4}-\d{2}-\d{2}$/.test(String(value ?? ""));
}

export function todayYMD(now = new Date()) {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function formatDateYMD(value, fallback = "ー") {
  if (!value) return fallback;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return fallback;
  const year = parsed.getFullYear();
  const month = String(parsed.getMonth() + 1).padStart(2, "0");
  const day = String(parsed.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function requiredDateMessage(label) {
  return `${label || "日付"}${MSG_DATE_REQUIRED}`;
}

export function invalidDateFormatMessage(label) {
  return `${label || "日付"}${MSG_DATE_FORMAT_INVALID}`;
}

export function validateRequiredDate(value, label) {
  if (!value) return requiredDateMessage(label);
  if (!isYmd(value)) return invalidDateFormatMessage(label);
  return "";
}

export function formatSlot(slot) {
  if (!slot) return "";
  const { slot_date: slotDate, slot_label: slotLabel } = slot;
  const parsed = slotDate ? new Date(`${slotDate}T00:00:00`) : null;
  const hasValidDate = parsed && !Number.isNaN(parsed.getTime());
  const dateStr = hasValidDate
    ? `${String(parsed.getMonth() + 1).padStart(2, "0")}/${String(
        parsed.getDate()
      ).padStart(2, "0")}（${DAYS_LABEL[parsed.getDay()]}）`
    : String(slotDate ?? "");
  return slotLabel ? `${dateStr} ${slotLabel}` : dateStr;
}

export function formatAnsweredAt(value) {
  return formatDateYMD(value);
}

export { DAYS_LABEL };
