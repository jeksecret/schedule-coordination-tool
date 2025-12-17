import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { fetchFacilityInfo, createSession, generateEvaluatorEmail } from "../services/sessionService";
import {
  isYmd,
  todayYMD,
  validateRequiredDate,
  requiredDateMessage,
  invalidDateFormatMessage,
} from "./utils/dateUtils";
import { PURPOSE_OPTIONS } from "./utils/constants";
import {
  MSG_NOTION_FETCH_FAILED,
  MSG_DUPLICATE_CANDIDATE,
  MSG_REQUIRE_NOTION_URL,
  MSG_REQUIRE_FACILITY_INFO,
  MSG_REQUIRE_FACILITY_CONTACT,
  MSG_REQUIRE_CANDIDATE_SLOT,
} from "./utils/messages";

export default function SessionCreate() {
  const nav = useNavigate();
  const { signOut } = useAuth();

  // form state
  const [notionUrl, setNotionUrl] = useState("");
  const [facilityName, setFacilityName] = useState("");
  const [contact, setContact] = useState({ name: "", email: "" });
  const [evaluators, setEvaluators] = useState([]);
  const [purpose, setPurpose] = useState("訪問調査");
  const [responseDeadline, setResponseDeadline] = useState("");
  const [presentationDate, setPresentationDate] = useState("");
  const [slots, setSlots] = useState([{ date: "", label: "" }]);

  // ui state
  const [loadingFetch, setLoadingFetch] = useState(false);
  const [saving, setSaving] = useState(false);
  const [fetchErr, setFetchErr] = useState("");
  const [inlineErr, setInlineErr] = useState("");
  const [showErrors, setShowErrors] = useState(false);

  const MIN_DATE = useMemo(() => todayYMD(), []);

  const resetFacilityBlock = () => {
    setFacilityName("");
    setContact({ name: "", email: "" });
    setEvaluators([]);
  };

  // 情報取得 → call backend (Notion API)
  const handleFetchInfo = async () => {
    if (!notionUrl) return;
    setFetchErr("");
    setInlineErr("");
    setLoadingFetch(true);
    resetFacilityBlock();
    const controller = new AbortController();
    try {
      const data = await fetchFacilityInfo(notionUrl, controller.signal);
      setFacilityName(data.facility_name || "");
      setContact(data.contact_person || { name: "", email: "" });
      setEvaluators(Array.isArray(data.evaluators) ? data.evaluators : []);
    } catch {
      resetFacilityBlock();
      setFetchErr(MSG_NOTION_FETCH_FAILED);
    } finally {
      setLoadingFetch(false);
    }
  };

  // Candidate rows add/remove/update
  const addSlotRow = () => setSlots((d) => [...d, { date: "", label: "" }]);
  const setSlotDate = (i, v) => {
    setInlineErr("");
    setSlots((d) => d.map((x, idx) => (idx === i ? { ...x, date: v } : x)));
  };
  const setSlotLabel = (i, v) => {
    setInlineErr("");
    setSlots((d) => d.map((x, idx) => (idx === i ? { ...x, label: v } : x)));
  };
  const removeSlot = (i) => {
    setInlineErr("");
    setSlots((d) => d.filter((_, idx) => idx !== i));
  };

  const validateCreateInputs = () => {
    const filled = slots.filter(
      (r) => r.date && r.date.trim() && r.label && r.label.trim()
    );

    const keys = filled.map((r) => `${r.date}|${r.label.trim()}`);
    const seen = new Set();
    for (const k of keys) {
      if (seen.has(k)) return MSG_DUPLICATE_CANDIDATE;
      seen.add(k);
    }

    if (!notionUrl?.trim()) return MSG_REQUIRE_NOTION_URL;
    if (!facilityName?.trim()) return MSG_REQUIRE_FACILITY_INFO;
    if (!contact?.name?.trim() || !contact?.email?.trim())
      return MSG_REQUIRE_FACILITY_CONTACT;
    if (filled.length === 0) return MSG_REQUIRE_CANDIDATE_SLOT;
    return null;
  };

  const responseDateError = validateRequiredDate(responseDeadline, "評価者回答期限");
  const presentationDateError = validateRequiredDate(presentationDate, "事業所提示期限");

  const slotDateErrors = useMemo(
    () =>
      slots.map((r) => {
        const hasAny = (r.date && r.date.trim()) || (r.label && r.label.trim());
        if (!hasAny) return "";
        if (!r.date) return requiredDateMessage("日付");
        if (!isYmd(r.date)) return invalidDateFormatMessage("日付");
        return "";
      }),
    [slots]
  );

  const canSubmit = !saving && validateCreateInputs() === null;

  // 保存して文面作成
  const handleCreate = async () => {
    setShowErrors(true);

    const hasSlotDateError = slotDateErrors.some(Boolean);
    if (responseDateError || presentationDateError || hasSlotDateError) {
      return;
    }

    const errMsg = validateCreateInputs();
    if (errMsg) {
      setInlineErr(errMsg);
      return;
    }

    setSaving(true);
    setInlineErr("");
    const controller = new AbortController();
    try {
      const candidate_slots = slots
        .filter((r) => r.date && r.date.trim() && r.label && r.label.trim())
        .map((r) => ({ slot_date: r.date, slot_label: r.label.trim() }));

      const payload = {
        notion_url: notionUrl,
        purpose,
        response_deadline: responseDeadline,
        presentation_date: presentationDate,
        candidate_slots,
      };

      const out = await createSession(payload, controller.signal);
      const sessionId = out.session_id;

      await generateEvaluatorEmail(sessionId, controller.signal);
      nav(`/session/${sessionId}/status`, { replace: true });
    } catch (e) {
      if (e?.name !== "AbortError") setInlineErr(String(e?.message || e));
    } finally {
      if (!controller.signal.aborted) setSaving(false);
    }
  };

  const handleLogout = async () => {
    await signOut();
    nav("/login", { replace: true });
  };

  const handleBack = () => nav("/session/list");

  return (
    <div className="min-h-screen bg-gray-200">
      {saving && (
        <div className="fixed inset-0 bg-white/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="p-4 rounded-xl border bg-white shadow">
            <div className="animate-spin w-5 h-5 border-2 border-blue-200 border-t-blue-600 rounded-full mx-auto mb-3"></div>
            <div className="text-xs">保存中…</div>
          </div>
        </div>
      )}

      {/* Top Navigation */}
      <nav className="bg-blue-500 text-white shadow">
        <div className="max-w-full mx-auto px-4 py-3 flex justify-end items-center">
          <button
            onClick={handleLogout}
            className="text-xs border border-white bg-transparent text-white font-light px-4 py-2 rounded hover:bg-white hover:text-blue-600"
          >
            ログアウト
          </button>
        </div>
      </nav>

      {/* Main content */}
      <main className="max-w-4xl mx-auto px-4 py-6">
        <div className="py-2">
          <button
            type="button"
            onClick={handleBack}
            className="flex items-center px-3 py-2 gap-1 rounded bg-blue-600 text-white text-xs hover:bg-blue-700"
          >
            一覧へ戻る
          </button>
        </div>

        {/* Loading (Notion fetch) */}
        {loadingFetch && (
          <div className="p-6 animate-pulse space-y-4 rounded-md bg-white border shadow-sm mb-4">
            <div className="h-6 w-48 bg-gray-200 rounded" />
            <div className="h-4 w-full bg-gray-200 rounded" />
            <div className="h-4 w-5/6 bg-gray-200 rounded" />
          </div>
        )}

        <div className="bg-white border rounded-lg p-4 space-y-4 shadow-sm">
          <h1 className="text-base font-medium text-gray-700">日程調整作成</h1>
          <hr className="my-3 border-gray-200" />

          {/* Notion URL */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-xs text-gray-700">Notion URL</div>
            <input
              className="flex-1 rounded border border-gray-300 px-3 py-2 text-xs"
              placeholder="https://www.notion.so/..."
              value={notionUrl}
              onChange={(e) => {
                const v = e.target.value;
                setInlineErr("");
                setFetchErr("");
                setNotionUrl(v);
                if (!v) resetFacilityBlock();
              }}
            />
            <button
              type="button"
              onClick={handleFetchInfo}
              disabled={loadingFetch || !notionUrl}
              className="px-3 py-2 rounded bg-blue-600 text-white text-xs hover:bg-blue-700 disabled:opacity-60"
            >
              {loadingFetch ? "取得中…" : "情報取得"}
            </button>

            {fetchErr && (
              <div className="w-full text-xs text-red-600 mt-1">{fetchErr}</div>
            )}
          </div>

          {/* 事業所情報（表示のみ） */}
          <div className="border rounded">
            <dl className="divide-y">
              <div className="flex items-center px-3 py-2">
                <dt className="w-36 text-xs text-gray-600">事業所名</dt>
                <dd className="flex-1 text-xs">
                  {facilityName ? <span className="text-gray-900">{facilityName}</span> : <span className="text-gray-400">－</span>}
                </dd>
              </div>
              <div className="flex items-center px-3 py-2">
                <dt className="w-36 text-xs text-gray-600">事業所担当者</dt>
                <dd className="flex-1 text-xs">
                  {contact?.name || contact?.email ? (
                    <span>
                      {contact.name || ""}
                      {contact.email ? (contact.name ? `（${contact.email}）` : contact.email) : ""}
                    </span>
                  ) : (
                    <span className="text-gray-400">－</span>
                  )}
                </dd>
              </div>
              <div className="flex items-start px-3 py-2">
                <dt className="w-36 text-xs text-gray-600 leading-7">評価者</dt>
                <dd className="flex-1 text-xs">
                  {evaluators?.length ? (
                    <ul className="space-y-1">
                      {evaluators.map((e, i) => (
                        <li key={i} className="leading-6">
                          {e.name}{e.email ? `（${e.email}）` : ""}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-gray-400">－</span>
                  )}
                </dd>
              </div>
            </dl>
          </div>

          {/* 調整情報入力 */}
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-36 text-xs text-gray-600">調査目的</div>
              <select
                className="w-36 rounded py-1 text-xs"
                value={purpose}
                onChange={(e) => {
                  setInlineErr("");
                  setPurpose(e.target.value);
                }}
              >
                {PURPOSE_OPTIONS.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-36 text-xs text-gray-600 mt-2">評価者回答期限</div>
              <div className="flex-1">
                <input
                  type="date"
                  className="w-36 rounded border-gray-300 py-1 text-xs"
                  value={responseDeadline}
                  onChange={(e) => {
                    setInlineErr("");
                    setResponseDeadline(e.target.value);
                  }}
                  min={MIN_DATE}
                />
                {showErrors && responseDateError && (
                  <div className="text-xs text-red-600 mt-1">{responseDateError}</div>
                )}
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-36 text-xs text-gray-600 mt-2">事業所提示期限</div>
              <div className="flex-1">
                <input
                  type="date"
                  className="w-36 rounded border-gray-300 py-1 text-xs"
                  value={presentationDate}
                  onChange={(e) => {
                    setInlineErr("");
                    setPresentationDate(e.target.value);
                  }}
                  min={MIN_DATE}
                />
                {showErrors && presentationDateError && (
                  <div className="text-xs text-red-600 mt-1">{presentationDateError}</div>
                )}
              </div>
            </div>
          </div>

          <div className="border rounded">
            <div className="flex items-start">
              <div className="w-36 text-xs text-gray-600 px-3 py-2">候補日程</div>
              <div className="flex-1 px-3 py-2 space-y-2">
                {slots.map((row, i) => (
                  <div key={i} className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                      <input
                        type="date"
                        className="w-36 rounded border-gray-300 py-1 text-xs"
                        value={row.date}
                        onChange={(e) => setSlotDate(i, e.target.value)}
                        min={MIN_DATE}
                      />
                      <input
                        type="text"
                        className="flex-1 rounded border border-gray-300 text-xs px-2 py-2"
                        value={row.label}
                        onChange={(e) => setSlotLabel(i, e.target.value)}
                      />
                      {slots.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeSlot(i)}
                          className="px-2 py-1 rounded border text-xs bg-red-600 hover:bg-red-700 text-white flex items-center gap-1"
                        >
                          削除
                        </button>
                      )}
                    </div>
                    {showErrors && slotDateErrors[i] && (
                      <div className="text-xs text-red-600">{slotDateErrors[i]}</div>
                    )}
                  </div>
                ))}
                <button
                  type="button"
                  onClick={addSlotRow}
                  className="mt-1 px-2 py-1 rounded border text-xs bg-blue-600 hover:bg-blue-700 text-white flex items-center gap-1"
                >
                  追加
                </button>
              </div>
            </div>
          </div>

          {inlineErr ? (
            <div className="text-xs text-red-600 text-center">{inlineErr}</div>
          ) : null}

          <div className="pt-2 flex justify-center">
            <button
              type="button"
              onClick={handleCreate}
              disabled={!canSubmit}
              className="w-full md:w-auto px-3 py-2 rounded bg-blue-600 text-white text-xs hover:bg-blue-700 disabled:opacity-60"
            >
              {saving ? "保存中…" : "保存して文面作成"}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
