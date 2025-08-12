import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const PURPOSE_OPTIONS = ["訪問調査", "聞き取り", "場面観察", "FB", "その他"];

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
  const [dates, setDates] = useState([""]); // candidate dates

  // ui state
  const [loadingFetch, setLoadingFetch] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  // 情報取得 → call backend (Notion API)
  const handleFetchInfo = async () => {
    if (!notionUrl) return;
    setErr("");
    setLoadingFetch(true);
    try {
      const res = await fetch(
        `/api/notion/facility-info?url=${encodeURIComponent(notionUrl)}`
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      setFacilityName(data.facility_name || "");
      setContact(data.contact_person || { name: "", email: "" });
      setEvaluators(Array.isArray(data.evaluators) ? data.evaluators : []);
    } catch (e) {
      setErr(String(e?.message || e));
    } finally {
      setLoadingFetch(false);
    }
  };

  // Add/remove candidate date rows
  const addDateRow = () => setDates((d) => [...d, ""]);
  const setDate = (i, v) =>
    setDates((d) => d.map((x, idx) => (idx === i ? v : x)));
  const removeDate = (i) => setDates((d) => d.filter((_, idx) => idx !== i));

  const handleLogout = async () => {
    await signOut();
    nav("/login", { replace: true });
  };

  return (
    <div className="min-h-screen bg-gray-200">
      {/* Top Navigation */}
      <nav className="bg-blue-500 text-white shadow">
        <div className="max-w-full mx-auto px-4 py-3 flex justify-end items-center">
          <button
            onClick={handleLogout}
            className="border border-white bg-transparent text-white font-light px-4 py-1 rounded hover:bg-white hover:text-blue-600 transition"
          >
            ログアウト
          </button>
        </div>
      </nav>

      {/* Main content */}
      <main className="max-w-3xl mx-auto px-4 py-6">
        <h1 className="text-lg font-semibold text-gray-800 mb-4">日程調整作成</h1>

        <div className="bg-white border rounded p-4 space-y-4">
          {/* Notion URL + 情報取得 */}
          <div className="flex gap-2">
            <input
              className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm"
              placeholder="https://www.notion.so/..."
              value={notionUrl}
              onChange={(e) => setNotionUrl(e.target.value)}
            />
            <button
              type="button"
              onClick={handleFetchInfo}
              disabled={loadingFetch || !notionUrl}
              className="px-3 py-2 rounded bg-blue-600 text-white text-sm hover:bg-blue-700 disabled:opacity-60"
            >
              {loadingFetch ? "取得中…" : "情報取得"}
            </button>
          </div>

          {/* 事業所情報（表示のみ） */}
          <div className="text-sm space-y-1">
            <div>
              <span className="text-gray-600">事業所名：</span>
              <span className="text-gray-800">{facilityName || "-"}</span>
            </div>
            <div>
              <span className="text-gray-600">事業所担当者：</span>
              {(contact?.name || contact?.email) ? (
                <span className="text-gray-800">
                  {contact.name || ""}
                  {contact.email
                    ? (contact.name ? `（${contact.email}）` : contact.email)
                    : ""}
                </span>
              ) : (
                <span className="text-gray-400">-</span>
              )}
            </div>
            <div className="text-gray-600">評価者：</div>
            <ul className="list-disc pl-6">
              {evaluators.length ? (
                evaluators.map((e, i) => (
                  <li key={i} className="text-gray-800">
                    {e.name}（{e.email}）
                  </li>
                ))
              ) : (
                <li className="text-gray-400">-</li>
              )}
            </ul>
          </div>

          {/* 調整情報入力 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <label className="text-sm">
              <div className="text-gray-600 mb-1">調査目的</div>
              <select
                className="w-full rounded border-gray-300 text-sm"
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
              >
                {PURPOSE_OPTIONS.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-sm">
              <div className="text-gray-600 mb-1">評価者回答期限</div>
              <input
                type="date"
                className="w-full rounded border-gray-300 text-sm"
                value={responseDeadline}
                onChange={(e) => setResponseDeadline(e.target.value)}
              />
            </label>

            <label className="text-sm">
              <div className="text-gray-600 mb-1">事業所提示予定日</div>
              <input
                type="date"
                className="w-full rounded border-gray-300 text-sm"
                value={presentationDate}
                onChange={(e) => setPresentationDate(e.target.value)}
              />
            </label>
          </div>

          {/* 候補日程 */}
          <div className="text-sm">
            <div className="text-gray-600 mb-1">候補日程</div>
            <div className="space-y-2">
              {dates.map((d, i) => (
                <div key={i} className="flex items-center gap-2">
                  <input
                    type="date"
                    className="rounded border-gray-300 text-sm"
                    value={d}
                    onChange={(e) => setDate(i, e.target.value)}
                  />
                  {dates.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeDate(i)}
                      className="px-2 py-1 rounded border text-xs"
                    >
                      削除
                    </button>
                  )}
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={addDateRow}
              className="mt-2 px-3 py-1.5 rounded border text-sm"
            >
              ＋ 追加
            </button>
          </div>

          {err && <div className="text-red-600 text-sm">{err}</div>}

          <div className="pt-2">
            <button
              type="button"
            //   onClick={handleCreate}
              disabled={saving || !facilityName || !contact.name || !contact.email}
              className="w-full md:w-auto px-4 py-2 rounded bg-blue-600 text-white text-sm hover:bg-blue-700 disabled:opacity-60"
            >
              {saving ? "保存中…" : "保存して文面作成"}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
