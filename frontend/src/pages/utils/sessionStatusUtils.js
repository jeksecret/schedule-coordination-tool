import {
  formatAnsweredAt,
  formatSlot,
  formatDateYMD,
  isYmd,
  requiredDateMessage,
  invalidDateFormatMessage,
  validateRequiredDate,
} from "./dateUtils";

export const TOKEN_TO_SYMBOL = { O: "○", M: "△", X: "x" };

const SYMBOL_TO_TOKEN = Object.fromEntries(
  Object.entries(TOKEN_TO_SYMBOL).map(([token, symbol]) => [symbol, token])
);

function normalizeAnswer(raw) {
  if (typeof raw !== "string") return "";
  const trimmed = raw.trim();
  if (!trimmed) return "";
  if (SYMBOL_TO_TOKEN[trimmed]) {
    return SYMBOL_TO_TOKEN[trimmed];
  }
  const upper = trimmed.toUpperCase();
  return TOKEN_TO_SYMBOL[upper] ? upper : "";
}

export function buildInitialAnswers(evaluators = [], slots = [], matrix = {}) {
  const answers = {};
  for (const evaluator of evaluators) {
    const evKey = evaluator?.id;
    const answerRow = matrix?.[String(evKey)] ?? matrix?.[evKey] ?? {};
    for (const slot of slots) {
      const slotKey = slot?.id;
      const raw = answerRow[String(slotKey)] ?? answerRow?.[slotKey] ?? "";
      answers[`${evKey}_${slotKey}`] = normalizeAnswer(raw);
    }
  }
  return answers;
}

export function buildInitialNotes(evaluators = []) {
  const notes = {};
  for (const evaluator of evaluators) {
    if (!evaluator) continue;
    notes[evaluator.id] = evaluator.note || "";
  }
  return notes;
}

export function buildInitialProposed(slots = []) {
  const proposed = {};
  for (const slot of slots) {
    if (!slot) continue;
    proposed[slot.id] = false;
  }
  return proposed;
}

export {
  formatAnsweredAt,
  formatSlot,
  formatDateYMD,
  isYmd,
  requiredDateMessage,
  invalidDateFormatMessage,
  validateRequiredDate,
};
