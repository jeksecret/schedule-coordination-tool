import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { PlusIcon, TrashIcon } from "@heroicons/react/24/outline";

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
  const [dates, setDates] = useState([""]);

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
      const res = await fetch(`/api/notion/facility-info?url=${encodeURIComponent(notionUrl)}`);
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
  const setDate = (i, v) => setDates((d) => d.map((x, idx) => (idx === i ? v : x)));
  const removeDate = (i) => setDates((d) => d.filter((_, idx) => idx !== i));

  const handleLogout = async () => {
    await signOut();
    nav("/login", { replace: true });
  };

  // (stub) create handler
  const handleCreate = async () => {
    setSaving(true);
    try {
      // TODO: POST to backend
    } finally {
      setSaving(false);
    }
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
        <h1 className="text-base font-semibold text-gray-800 mb-3">日程調整作成</h1>

        <div className="bg-white border rounded-lg p-4 space-y-4 shadow-sm">
          {/* Notion URL + 情報取得 */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-sm text-gray-700">Notion URL</div>
            <input
              className="flex-1 min-w-[200px] rounded border border-gray-300 px-3 py-2 text-sm"
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
          <div className="border rounded">
            <dl className="divide-y">
              <div className="flex items-center px-3 py-2">
                <dt className="w-36 text-xs text-gray-600">事業所名</dt>
                <dd className="flex-1 text-sm">
                  {facilityName ? (
                    <span className="text-gray-900">{facilityName}</span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </dd>
              </div>
              <div className="flex items-center px-3 py-2">
                <dt className="w-36 text-xs text-gray-600">事業所担当者</dt>
                <dd className="flex-1 text-sm">
                  {(contact?.name || contact?.email) ? (
                    <span>
                      {contact.name || ""}
                      {contact.email ? (contact.name ? `（${contact.email}）` : contact.email) : ""}
                    </span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </dd>
              </div>
              <div className="flex items-start px-3 py-2">
                <dt className="w-36 text-xs text-gray-600 leading-7">評価者</dt>
                <dd className="flex-1 text-sm">
                  {evaluators?.length ? (
                    <ul className="space-y-1">
                      {evaluators.map((e, i) => (
                        <li key={i} className="leading-6">
                          {e.name}{e.email ? `（${e.email}）` : ""}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-gray-400">-</span>
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
                className="w-48 rounded border-gray-300 py-1 text-sm"
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
              >
                {PURPOSE_OPTIONS.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-3">
              <div className="w-36 text-xs text-gray-600">評価者回答期限</div>
              <input
                type="date"
                className="w-48 rounded border-gray-300 py-1 text-sm"
                value={responseDeadline}
                onChange={(e) => setResponseDeadline(e.target.value)}
              />
            </div>

            <div className="flex items-center gap-3">
              <div className="w-36 text-xs text-gray-600">事業所提示期限</div>
              <input
                type="date"
                className="w-48 rounded border-gray-300 py-1 text-sm"
                value={presentationDate}
                onChange={(e) => setPresentationDate(e.target.value)}
              />
            </div>
          </div>

          {/* 候補日程 */}
          <div className="border rounded">
            <div className="flex items-start">
              <div className="w-36 text-xs text-gray-600 px-3 py-2">候補日程</div>
              <div className="flex-1 px-3 py-2 space-y-2">
                {dates.map((d, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <input
                      type="date"
                      className="w-48 rounded border-gray-300 text-sm"
                      value={d}
                      onChange={(e) => setDate(i, e.target.value)}
                    />
                    {dates.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeDate(i)}
                        className="px-2 py-1 rounded border text-xs hover:bg-red-500 hover:text-white transition flex items-center gap-1"
                      >
                        <TrashIcon className="w-4 h-4" /> 削除
                      </button>
                    )}
                  </div>
                ))}
                <button
                  type="button"
                  onClick={addDateRow}
                  className="mt-1 px-2 py-1 rounded border text-sm hover:bg-blue-500 hover:text-white transition flex items-center gap-1"
                >
                  <PlusIcon className="w-4 h-4" /> 追加
                </button>
              </div>
            </div>
          </div>

          {err && <div className="text-red-600 text-sm">{err}</div>}

          <div className="pt-2 flex justify-center">
            <button
              type="button"
              onClick={handleCreate}
              disabled={saving || !facilityName || !contact.name || !contact.email}
              className="w-full md:w-auto px-3 py-2 rounded bg-blue-600 text-white text-sm hover:bg-blue-700 disabled:opacity-60"
            >
              {saving ? "保存中…" : "保存して文面作成"}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
