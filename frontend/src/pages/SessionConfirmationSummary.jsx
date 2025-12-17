import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { fetchConfirmationSummary } from "../services/sessionService";
import { formatDateYMD } from "./utils/dateUtils";

export default function InternalSessionSummary() {
  const { signOut } = useAuth();
  const nav = useNavigate();
  const { id } = useParams();

  const [row, setRow] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    setLoading(true);
    setErr("");

    (async () => {
      try {
        const data = await fetchConfirmationSummary(Number(id), controller.signal);
        if (!active) return;
        setRow(data);
      } catch (e) {
        if (e?.name === "AbortError" || !active) return;
        setRow(null);
        setErr(String(e?.message || e));
      } finally {
        if (active && !controller.signal.aborted) {
          setLoading(false);
        }
      }
    })();

    return () => {
      active = false;
      controller.abort();
    };
  }, [id]);

  const contactEmails = useMemo(() => {
    const list = [];
    if (row?.facility_contact_email) list.push(row.facility_contact_email);
    if (Array.isArray(row?.facility_contact_emails)) list.push(...row.facility_contact_emails);
    return Array.from(new Set(list)).filter(Boolean);
  }, [row]);

  const evaluators = useMemo(
    () => (Array.isArray(row?.evaluators) ? row.evaluators : []),
    [row]
  );

  const handleLogout = async () => {
    await signOut();
    nav("/login", { replace: true });
  };

  const handleBack = () => nav("/session/list");

  return (
    <div className="min-h-screen bg-gray-200">
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
      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="py-2">
          <button
            type="button"
            onClick={handleBack}
            className="flex items-center px-3 py-2 gap-1 rounded bg-blue-600 text-white text-xs hover:bg-blue-700"
          >
            一覧へ戻る
          </button>
        </div>

        {/* Loading */}
        {loading && (
          <div className="p-6 animate-pulse space-y-4 rounded-md bg-white border shadow-sm">
            <div className="h-6 w-48 bg-gray-200 rounded" />
            <div className="h-4 w-full bg-gray-200 rounded" />
            <div className="h-4 w-5/6 bg-gray-200 rounded" />
          </div>
        )}

        {/* Error */}
        {!loading && err && (
          <div className="p-6 rounded-md bg-white border shadow-sm">
            <div className="text-red-600 text-xs">{err}</div>
          </div>
        )}

        {/* Content */}
        {!loading && !err && row && (
          <div className="space-y-6">
            {/* 基本情報 */}
            <div className="bg-white border rounded shadow-sm p-4">
              <h2 className="text-base font-medium text-gray-700">基本情報</h2>
              <hr className="my-3 border-gray-200" />
              <dl className="divide-y">
                {/* 事業所名 */}
                <div className="flex items-center py-2">
                  <dt className="w-36 text-xs text-gray-600">事業所名</dt>
                  <dd className="flex-1 text-xs">
                    {row.facility_notion_url ? (
                      <a
                        className="text-blue-700 hover:underline break-all"
                        href={row.facility_notion_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {row.facility_name}
                      </a>
                    ) : (
                      <span className="text-gray-900">{row.facility_name || "ー"}</span>
                    )}
                  </dd>
                </div>

                {/* 事業所担当者 */}
                <div className="flex items-center py-2">
                  <dt className="w-36 text-xs text-gray-600">事業所担当者</dt>
                  <dd className="flex-1 text-xs">
                    {row.facility_contact_name || contactEmails.length ? (
                      <span>
                        {row.facility_contact_name || ""}
                        {contactEmails.length
                          ? `（${contactEmails.join(" ")}）`
                          : ""}
                      </span>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </dd>
                </div>

                {/* 調査目的 */}
                <div className="flex items-center py-2">
                  <dt className="w-36 text-xs text-gray-600">調査目的</dt>
                  <dd className="flex-1 text-xs">
                    {row.purpose || <span className="text-gray-400">-</span>}
                  </dd>
                </div>

                {/* ステータス */}
                <div className="flex items-center py-2">
                  <dt className="w-36 text-xs text-gray-600">ステータス</dt>
                  <dd className="flex-1 text-xs">
                    {row.status || <span className="text-gray-400">-</span>}
                  </dd>
                </div>
              </dl>
            </div>

            {/* 事業所回答 */}
            <div className="bg-white border rounded shadow-sm p-4">
              <h2 className="text-base font-medium text-gray-700">事業所回答</h2>
              <hr className="my-3 border-gray-200" />
              <dl className="divide-y">
                <div className="flex items-center py-2">
                  <dt className="w-36 text-xs text-gray-600">回答日</dt>
                  <dd className="flex-1 text-xs">{formatDateYMD(row.client_answered_at)}</dd>
                </div>
                <div className="flex items-center py-2">
                  <dt className="w-36 text-xs text-gray-600 leading-7">希望日程</dt>
                  <dd className="flex-1 text-xs">
                    {row.preferred_slot_id ? (
                      <div className="flex flex-wrap items-center gap-x-1 gap-y-1">
                        <span className="text-gray-900">{formatDateYMD(row.preferred_slot_date)}</span>
                        <span className="text-gray-900">{row.preferred_slot_label || "—"}</span>
                      </div>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </dd>
                </div>
                <div className="flex items-center py-2">
                  <dt className="w-36 text-xs text-gray-600 leading-7">備考</dt>
                  <dd className="flex-1 text-xs whitespace-pre-wrap">
                    {row.client_note || <span className="text-gray-400">－</span>}
                  </dd>
                </div>
              </dl>
            </div>

            {/* 評価者 */}
            <div className="bg-white border rounded shadow-sm p-4">
              <h2 className="text-base font-medium text-gray-700">評価者</h2>
              <hr className="my-3 border-gray-200" />
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs">
                  <thead>
                    <tr className="text-left text-gray-500">
                      <th className="py-2 pr-4">氏名</th>
                      <th className="py-2 pr-4">メールアドレス</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Array.isArray(evaluators) && evaluators.length > 0 ? (
                      evaluators.map((ev) => (
                        <tr key={ev.id} className="border-t">
                          <td className="py-2 pr-4">{ev.name}</td>
                          <td className="py-2 pr-4">{ev.email}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="2" className="py-3 text-gray-500">
                          評価者がいません
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
