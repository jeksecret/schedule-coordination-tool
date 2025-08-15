import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  ChevronDoubleLeftIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronDoubleRightIcon
} from "@heroicons/react/24/solid";
import { fetchEnums, fetchSessionList } from "../services/sessionService";

const DEFAULT_PURPOSE = ["訪問調査", "聞き取り", "場面観察", "FB", "その他"];
const DEFAULT_STATUS   = ["起案中", "評価者待ち", "事業所待ち", "確定"];
const PAGE_SIZE = 10;

const toOptions = (arr) => [{ value: "", label: "すべて" }, ...arr.map(v => ({ value: v, label: v }))];

export default function SessionList() {
  const { signOut } = useAuth();
  const nav = useNavigate();
  const location = useLocation();

  const incomingAlert = location.state?.alert || null;
  const [alert, setAlert] = useState(incomingAlert);

  useEffect(() => {
    if (incomingAlert) {
      nav("/session/list", { replace: true, state: null });
    }
  }, []);

  // Filter options
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
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  // pagination
  const [page, setPage] = useState(1);
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const startIndex = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const endIndex = total === 0 ? 0 : Math.min(page * PAGE_SIZE, total);

  // load enums once
  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      try {
        const data = await fetchEnums(controller.signal);
        const p = Array.isArray(data.purpose) && data.purpose.length ? data.purpose : DEFAULT_PURPOSE;
        const s = Array.isArray(data.status)  && data.status.length  ? data.status  : DEFAULT_STATUS;
        setPurposeOptions(toOptions(p));
        setStatusOptions(toOptions(s));
        if (purpose && !p.includes(purpose)) setPurpose("");
        if (status && !s.includes(status)) setStatus("");
      } catch {
        /* fallback to defaults */
      }
    })();
    return () => controller.abort();
  }, [purpose, status]);

  const handleSearch = () => {
    setCommittedPurpose(purpose);
    setCommittedStatus(status);
    setCommittedFacility(facilityQuery);
    setPage(1);
  };

  // fetch data when committed filters or page change
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setLoading(true);
    setErr("");
    (async () => {
      try {
        const out = await fetchSessionList(
          {
            purpose: committedPurpose,
            status: committedStatus,
            facility: committedFacility,
            page,
            page_size: PAGE_SIZE,
          },
          controller.signal
        );
        if (!active) return;
        const mapped = (out.items || []).map((r) => ({
          id: r.id,
          facilityName: r.facility_name,
          purpose: r.purpose,
          status: r.status,
          confirmedDate: r.confirmed_date ? String(r.confirmed_date).replaceAll("-", "/") : "-",
          notionUrl: r.notion_url,
          progress: {
            done: r.answered ?? 0,
            total: r.total_evaluators ?? 0,
          },
          hasClientResponse: Boolean(r.client_answered_at || r.confirmed_date),
        }));
        setRows(mapped);
        setTotal(out.total ?? mapped.length);
      } catch (e) {
        if (e?.name === "AbortError" || !active) return;
        setErr(String(e?.message || e));
      } finally {
        if (!active || controller.signal.aborted) return;
        setLoading(false);
      }
    })();
    return () => {
      active = false;
      controller.abort();
    };
  }, [committedPurpose, committedStatus, committedFacility, page]);

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
            className="border border-white bg-transparent text-white font-light px-4 py-1 rounded hover:bg-white hover:text-blue-600"
          >
            ログアウト
          </button>
        </div>
      </nav>

      {/* Alert banner */}
      {alert && (
        <div className="max-w-7xl mx-auto px-3">
          <div className="mt-3 rounded-lg border border-red-500/60 bg-slate-800 text-slate-100 shadow">
            <div className="p-3">
              <div className="flex items-start gap-2">
                <div className="flex-1">
                  <div className="text-sm font-medium text-red-300">
                    {alert.title || "This is a danger alert"}
                  </div>
                  <p className="mt-0.5 text-xs text-slate-200/90">
                    {alert.message || "More info about this alert goes here."}
                  </p>
                  <div className="mt-2 flex items-center gap-2">
                    {alert.href && (
                      <a
                        href={alert.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center rounded-md border border-red-500/60 px-2 py-1 text-xs text-red-200 hover:bg-red-500/10"
                      >
                        {alert.actionLabel || "開く"}
                      </a>
                    )}
                    <button
                      onClick={() => setAlert(null)}
                      className="inline-flex items-center rounded-md border border-slate-600 px-2 py-1 text-xs text-slate-200 hover:bg-white/5"
                      aria-label="閉じる"
                    >
                      閉じる
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Header */}
        <header>
          <div className="flex items-center justify-between py-2">
            <h1 className="text-base font-medium text-gray-700">日程調整一覧</h1>
            <button
              onClick={() => nav("/session/create")}
              className="px-3 py-2 rounded bg-blue-600 text-white text-sm hover:bg-blue-700"
            >
              新規作成
            </button>
          </div>
        </header>

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
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div className="flex md:justify-end">
              <button
                onClick={handleSearch}
                className="px-3 py-2 rounded bg-blue-600 text-white text-sm hover:bg-blue-700 w-full md:w-auto"
              >
                検索
              </button>
            </div>
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <div className="p-6 animate-pulse space-y-4 rounded-md bg-white border shadow-sm mt-4">
            <div className="h-6 w-48 bg-gray-200 rounded" />
            <div className="h-4 w-full bg-gray-200 rounded" />
            <div className="h-4 w-5/6 bg-gray-200 rounded" />
          </div>
        )}

        {/* Error */}
        {!loading && err && (
          <div className="mt-4 rounded-md border border-red-200 bg-red-50 text-red-700 px-3 py-2 text-sm">
            読み込みエラー: {err}
          </div>
        )}

        {/* Table */}
        {!loading && !err && (
          <div className="mt-4 overflow-hidden rounded-md border border-gray-200 bg-white shadow-sm">
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50 text-gray-600">
                  <tr className="[&>th]:px-3 [&>th]:py-2 [&>th]:text-left">
                    <th className="w-16">id</th>
                    <th className="w-auto">事業所名</th>
                    <th className="w-28">調査目的</th>
                    <th className="w-28">ステータス</th>
                    <th className="w-28">評価者進捗</th>
                    <th className="w-32">確定日程</th>
                    <th className="w-28"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {rows.length === 0 && (
                    <tr>
                      <td colSpan={7} className="p-6 text-center text-gray-500">
                        該当するデータがありません
                      </td>
                    </tr>
                  )}
                  {rows.map((r) => (
                    <tr key={r.id} className="[&>td]:px-3 [&>td]:py-2 hover:bg-blue-50/40">
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
                      <td><StatusBadge status={r.status} /></td>
                      <td className="tabular-nums">{r.progress.done} / {r.progress.total}</td>
                      <td className="tabular-nums">{r.confirmedDate}</td>
                      <td>
                        <div className="flex gap-2">
                          <button
                            onClick={() => nav(`/session/${r.id}/status`)}
                            className="px-2 py-1 rounded bg-blue-600 text-white text-xs hover:bg-blue-700"
                          >
                            詳細
                          </button>
                          <button
                            onClick={() => nav(`/session/${r.id}/confirmation-summary`)}
                            disabled={!r.hasClientResponse}
                            className={`px-2 py-1 rounded text-xs ${
                              r.hasClientResponse
                                ? "bg-emerald-600 text-white hover:bg-emerald-700"
                                : "bg-gray-200 text-gray-500 cursor-not-allowed"
                            }`}
                            title={r.hasClientResponse ? "" : "事業所の回答がまだありません"}
                          >
                            確認
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {total > 0 && (
              <div className="flex items-center justify-between px-4 py-3 border-t">
                <div className="text-xs text-gray-600">
                  {`${startIndex}–${endIndex} / ${total}`}
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage(1)}
                    disabled={page === 1}
                    className="px-2 py-1 text-xs border rounded disabled:opacity-50 flex items-center"
                  >
                    <ChevronDoubleLeftIcon className="w-4 h-4" />
                    <span className="sr-only">First</span>
                  </button>
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-2 py-1 text-xs border rounded disabled:opacity-50 flex items-center"
                  >
                    <ChevronLeftIcon className="w-4 h-4" />
                    <span className="sr-only">Prev</span>
                  </button>
                  <span className="px-2 text-xs text-gray-700">
                    Page {page} / {pageCount}
                  </span>
                  <button
                    onClick={() => setPage(p => Math.min(pageCount, p + 1))}
                    disabled={page === pageCount}
                    className="px-2 py-1 text-xs border rounded disabled:opacity-50 flex items-center"
                  >
                    <ChevronRightIcon className="w-4 h-4" />
                    <span className="sr-only">Next</span>
                  </button>
                  <button
                    onClick={() => setPage(pageCount)}
                    disabled={page === pageCount}
                    className="px-2 py-1 text-xs border rounded disabled:opacity-50 flex items-center"
                  >
                    <ChevronDoubleRightIcon className="w-4 h-4" />
                    <span className="sr-only">Last</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    "確定":     "bg-emerald-100 text-emerald-700",
    "評価者待ち": "bg-amber-100 text-amber-700",
    "事業所待ち": "bg-sky-100 text-sky-700",
    "起案中":     "bg-gray-100 text-gray-700",
  };
  const style = map[status] || "bg-indigo-100 text-indigo-700";
  return <span className={`px-2 py-0.5 text-xs rounded ${style}`}>{status}</span>;
}
