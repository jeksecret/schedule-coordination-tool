import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// Fallbacks (used until /meta/enums loads or if it fails)
const DEFAULT_PURPOSE = ["訪問調査", "聞き取り", "場面観察", "FB", "その他"];
const DEFAULT_STATUS  = ["起案中", "評価者待ち", "事業所待ち", "確定"];

const toOptions = (arr) => [{ value: "", label: "すべて" }, ...arr.map(v => ({ value: v, label: v }))];

export default function Dashboard() {
  const nav = useNavigate();
  const { signOut } = useAuth();

  // Filter options loaded from backend (with fallback defaults)
  const [purposeOptions, setPurposeOptions] = useState(toOptions(DEFAULT_PURPOSE));
  const [statusOptions,  setStatusOptions]  = useState(toOptions(DEFAULT_STATUS));

  // UI (uncommitted) filters
  const [purpose, setPurpose] = useState("");
  const [status, setStatus] = useState("");
  const [facilityQuery, setFacilityQuery] = useState("");

  // committed filters
  const [committedPurpose, setCommittedPurpose] = useState("");
  const [committedStatus, setCommittedStatus] = useState("");
  const [committedFacility, setCommittedFacility] = useState("");

  // data state
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  // Load enum values from backend (once)
  useEffect(() => {
    let ignore = false;
    (async () => {
      try {
        const res = await fetch("/api/meta/enums", { credentials: "include" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json(); // { purpose: [...], status: [...] }
        if (ignore) return;

        const p = Array.isArray(data.purpose) && data.purpose.length ? data.purpose : DEFAULT_PURPOSE;
        const s = Array.isArray(data.status)  && data.status.length  ? data.status  : DEFAULT_STATUS;

        setPurposeOptions(toOptions(p));
        setStatusOptions(toOptions(s));

        // Ensure current selections are valid (if options changed)
        if (purpose && !p.includes(purpose)) setPurpose("");
        if (status  && !s.includes(status))  setStatus("");

      } catch {
        // keep fallbacks silently
      }
    })();
    return () => { ignore = true; };
  }, []); // run once

  const handleSearch = () => {
    setCommittedPurpose(purpose);
    setCommittedStatus(status);
    setCommittedFacility(facilityQuery);
  };

  // Fetch table data when committed filters change
  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;

    const qs = new URLSearchParams();
    if (committedPurpose) qs.set("purpose", committedPurpose);
    if (committedStatus) qs.set("status", committedStatus);
    if (committedFacility) qs.set("facility", committedFacility);

    (async () => {
      setLoading(true);
      setErr("");
      try {
        const res = await fetch(`/api/session/list?${qs.toString()}`, {
          credentials: "include",
          signal,
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (signal.aborted) return;

        const mapped = data.map((r) => ({
          id: r.id,
          facilityName: r.facility_name,
          purpose: r.purpose,
          status: r.status,
          confirmedDate: String(r.confirmed_date ?? "-").replaceAll("-", "/"),
          notionUrl: r.notion_url,
          progress: { done: 0, total: 0 }, // placeholder until progress is implemented
        }));
        setRows(mapped);
      } catch (e) {
        if (e?.name === "AbortError") return;
        setErr(String(e?.message || e));
      } finally {
        if (!signal.aborted) setLoading(false);
      }
    })();

    return () => controller.abort();
  }, [committedPurpose, committedStatus, committedFacility]);

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

      {/* Page header */}
      <header>
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="text-lg font-semibold text-gray-800">日程調整一覧</div>
          <button
            onClick={() => nav("/session/create")}
            className="px-3 py-2.5 rounded bg-blue-600 text-white text-sm hover:bg-blue-700"
          >
            新規作成
          </button>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Filters */}
        <div className="rounded-md bg-white shadow-sm border border-gray-200 p-4">
          <div className="grid grid-cols-1 md:grid-cols-[220px,220px,1fr,120px] gap-3">
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600 w-20">調査目的</label>
              <select
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                className="w-full rounded border border-gray-300 py-2 text-sm focus:ring-blue-500 focus:border-blue-500"
              >
                {purposeOptions.map((o) => (
                  <option key={o.value + o.label} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600 w-28">ステータス</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="w-full rounded border border-gray-300 py-2 text-sm focus:ring-blue-500 focus:border-blue-500"
              >
                {statusOptions.map((o) => (
                  <option key={o.value + o.label} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600 whitespace-nowrap">
                事業所名
              </label>
              <input
                value={facilityQuery}
                onChange={(e) => setFacilityQuery(e.target.value)}
                placeholder="事業所名..."
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div className="flex md:justify-end">
              <button
                onClick={handleSearch}
                className="px-4 py-2 rounded bg-blue-600 text-white text-sm hover:bg-blue-700 w-full md:w-auto"
              >
                検索
              </button>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="mt-4 overflow-hidden rounded-md border border-gray-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-gray-600">
                <tr className="[&>th]:px-3 [&>th]:py-2 [&>th]:text-left">
                  <th className="w-16">id</th>
                  <th>事業所名</th>
                  <th className="w-28">調査目的</th>
                  <th className="w-28">ステータス</th>
                  <th className="w-28">評価者進捗</th>
                  <th className="w-32">確定日程</th>
                  <th className="w-20"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {loading && (
                  <tr>
                    <td colSpan={7} className="p-6 text-center text-gray-500">
                      読み込み中…
                    </td>
                  </tr>
                )}
                {!loading && err && (
                  <tr>
                    <td colSpan={7} className="p-6 text-center text-red-600">
                      読み込みエラー: {err}
                    </td>
                  </tr>
                )}
                {!loading && !err && rows.length === 0 && (
                  <tr>
                    <td colSpan={7} className="p-6 text-center text-gray-500">
                      該当するデータがありません
                    </td>
                  </tr>
                )}
                {!loading &&
                  !err &&
                  rows.map((r) => (
                    <tr
                      key={r.id}
                      className="[&>td]:px-3 [&>td]:py-2 hover:bg-blue-50/40"
                    >
                      <td className="text-gray-600">{r.id}</td>
                      <td>
                        {r.notionUrl ? (
                          <a
                            href={r.notionUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="text-blue-700 hover:underline"
                          >
                            {r.facilityName}
                          </a>
                        ) : (
                          <span className="text-blue-700">{r.facilityName}</span>
                        )}
                      </td>
                      <td>{r.purpose}</td>
                      <td>
                        <StatusBadge status={r.status} />
                      </td>
                      <td className="tabular-nums">
                        {r.progress.done} / {r.progress.total}
                      </td>
                      <td className="tabular-nums">{r.confirmedDate}</td>
                      <td>
                        <button
                          onClick={() => nav(`/session/${r.id}/status`)}
                          className="px-2 py-1 rounded bg-blue-600 text-white text-xs hover:bg-blue-700"
                        >
                          詳細
                        </button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}

function StatusBadge({ status }) {
  const style =
    status === "確定"
      ? "bg-emerald-100 text-emerald-700"
      : status === "評価者待ち"
      ? "bg-amber-100 text-amber-700"
      : "bg-indigo-100 text-indigo-700";
  return (
    <span className={`px-2 py-0.5 text-xs rounded ${style}`}>{status}</span>
  );
}
