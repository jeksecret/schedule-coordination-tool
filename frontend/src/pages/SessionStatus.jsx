import { useEffect, useState, useCallback, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  fetchSessionStatus,
  updateEvaluatorResponses,
  updateSession,
  checkSlotEveryoneOk,
  generateFacilityEmail,
  extractGmailDraftUrl
} from "../services/sessionService";

const PURPOSE_OPTIONS = ["訪問調査", "聞き取り", "場面観察", "FB", "その他"];
const DAYS_LABEL = ["日", "月", "火", "水", "木", "金", "土"];
const TOKEN_TO_SYMBOL = { O: "○", M: "△", X: "x" };
const isYmd = (s) => /^\d{4}-\d{2}-\d{2}$/.test(String(s || ""));

export default function SessionStatus() {
  const { signOut } = useAuth();
  const nav = useNavigate();

  // data state
  const { id } = useParams();
  const [loading, setLoading] = useState(false);
  const [pageErr, setPageErr] = useState("");
  const [inlineErr, setInlineErr] = useState("");
  const [data, setData] = useState(null);
  const [saving, setSaving] = useState(false);
  const [makingDraft, setMakingDraft] = useState(false);

  // local state (editable)
  const [purpose, setPurpose] = useState("");
  const [responseDeadline, setResponseDeadline] = useState("");
  const [presentationDate, setPresentationDate] = useState("");
  const [showDateErrors, setShowDateErrors] = useState(false);

  // matrix state for answers & notes
  const [localAnswers, setLocalAnswers] = useState({});
  const [notes, setNotes] = useState({});
  const [proposed, setProposed] = useState({});

  const hasProposedSelected = useMemo(
    () => Object.values(proposed || {}).some(Boolean),
    [proposed]
  );

  // centralized loader
  const reloadStatus = useCallback(
    async (abortSignal) => {
      const out = await fetchSessionStatus(id, abortSignal);
      setData(out);
    },
    [id]
  );

  // initial load
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setPageErr("");
    reloadStatus(controller.signal)
      .catch((e) => {
        if (e?.name !== "AbortError") setPageErr(String(e?.message || e));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [id, reloadStatus]);

  // local UI state from fetched data
  useEffect(() => {
    if (!data?.session) return;

    setPurpose(data.session.purpose || "");
    setResponseDeadline(data.session.response_deadline || "");
    setPresentationDate(data.session.presentation_date || "");

    // initialize answers to blank
    const initAns = {};
    for (const ev of data.evaluators || []) {
      for (const slot of data.slots || []) {
        initAns[`${ev.id}_${slot.id}`] = "";
      }
    }
    setLocalAnswers(initAns);

    // notes
    const initNotes = {};
    for (const ev of data.evaluators || []) {
      initNotes[ev.id] = ev.note || "";
    }
    setNotes(initNotes);

    // checkboxes
    const initProp = {};
    for (const s of data.slots || []) initProp[s.id] = false;
    setProposed(initProp);
  }, [data]);

  const getAns = (eId, sId) => localAnswers[`${eId}_${sId}`] ?? "";
  const setAns = (eId, sId, v) => setLocalAnswers((m) => ({ ...m, [`${eId}_${sId}`]: v }));

  const responseDateError =
    !responseDeadline
      ? "評価者回答期限を入力してください。"
      : !isYmd(responseDeadline)
      ? "評価者回答期限の日付形式が正しくありません。"
      : "";

  const presentationDateError =
    !presentationDate
      ? "事業所提示期限を入力してください。"
      : !isYmd(presentationDate)
      ? "事業所提示期限の日付形式が正しくありません。"
      : "";

  // aggregate when checked
  const handleProposedCheck = async (slotId, nextChecked) => {
    const controller = new AbortController();
    setInlineErr("");
    if (!nextChecked) {
      setProposed((m) => ({ ...m, [slotId]: false }));
      setLocalAnswers((m) => {
        const next = { ...m };
        for (const ev of data.evaluators || []) {
          next[`${ev.id}_${slotId}`] = "";
        }
        return next;
      });
      return;
    }
    try {
      const out = await checkSlotEveryoneOk(
        data.session.id,
        slotId,
        controller.signal
      );
      const ok = !!out?.everyone_ok;
      setProposed((m) => ({ ...m, [slotId]: ok }));
      if (!ok) {
        setInlineErr("全員が「○」のときのみチェックできます。");
        return;
      }
      setLocalAnswers((m) => {
        const next = { ...m };
        for (const ev of data.evaluators || []) {
          next[`${ev.id}_${slotId}`] = "O";
        }
        return next;
      });
    } catch (e) {
      if (e?.name !== "AbortError") setInlineErr(String(e?.message || e));
    }
  };

  const handleUpdateSession = async () => {
    setInlineErr("");
    setShowDateErrors(true);

    if (responseDateError || presentationDateError) {
      return;
    }

    const controller = new AbortController();
    setSaving(true);
    try {
      const payload = {
        ...(purpose?.trim() ? { purpose: purpose.trim() } : {}),
        ...(responseDeadline ? { response_deadline: responseDeadline } : {}),
        ...(presentationDate ? { presentation_date: presentationDate } : {}),
      };
      if (Object.keys(payload).length === 0) return;
      await updateSession(data.session.id, payload, controller.signal);
      await reloadStatus(controller.signal);
    } catch (e) {
      if (e?.name !== "AbortError") setInlineErr(String(e?.message || e));
    } finally {
      if (!controller.signal.aborted) setSaving(false);
    }
  };

  // per-evaluator save
  const handleUpdateEvaluatorResponse = async (evaluatorId) => {
    const controller = new AbortController();
    setSaving(true);
    setInlineErr("");
    try {
      const payload = {
        note: notes[evaluatorId] || "",
        answers: Object.fromEntries(
          (data?.slots || []).map((s) => [s.id, getAns(evaluatorId, s.id) || ""])
        ),
      };
      await updateEvaluatorResponses(
        data.session.id,
        evaluatorId,
        payload,
        controller.signal
      );
    } catch (e) {
      if (e?.name !== "AbortError") setInlineErr(String(e?.message || e));
    } finally {
      if (!controller.signal.aborted) setSaving(false);
    }
  };

  const handleMakeFacilityEmailDraft = async () => {
    setInlineErr("");

    const checked = (data?.slots ?? []).filter(s => !!proposed[s.id]).map(s => s.id);
    if (!checked.length) {
      setInlineErr("事業所提案にチェックされた候補がありません。少なくとも1件選択してください。");
      return;
    }

    const controller = new AbortController();
    setMakingDraft(true);
    const defaultTimeout = 120000;
    const timeoutId = setTimeout(() => controller.abort(), defaultTimeout);

    try {
      const res = await generateFacilityEmail(data.session.id, checked, controller.signal);
      const url = extractGmailDraftUrl(res);

      if (!url) {
        setInlineErr("Gmail下書きURLの取得に失敗しました。しばらくしてからもう一度お試しください。");
        return;
      }

      const win = window.open(url, "_blank");
      if (win) {
        try { win.opener = null; } catch {}
        try { setTimeout(() => win.focus?.(), 50); } catch {}
      }

      const popupBlocked = !win;
      nav("/session/list", {
        replace: true,
        state: popupBlocked
          ? {
              alert: {
                title: "ポップアップがブロックされました",
                message: "ブラウザのポップアップ設定を許可するか、下のボタンからGmail下書きを開いてください。",
                actionLabel: "Gmail下書きを開く",
                href: url,
              },
            }
          : undefined,
      });
    } catch (e) {
      setInlineErr(
        e?.name === "AbortError"
          ? "タイムアウトしました。もう一度お試しください。"
          : (e?.message || "下書き作成でエラーが発生しました。")
      );
    } finally {
      clearTimeout(timeoutId);
      setMakingDraft(false);
    }
  };

  const handleLogout = async () => {
    await signOut();
    nav("/login", { replace: true });
  };

  const handleBack = () => nav("/session/list");

  const formatAnsweredAt = (answeredAt) => {
    if (!answeredAt) return "ー";
    const d = new Date(answeredAt);
    if (isNaN(d.getTime())) return "ー";
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
      d.getDate()
    ).padStart(2, "0")}`;
  };

  const formatSlot = (slot) => {
    const d = new Date(`${slot.slot_date}T00:00:00`);
    const dateStr = isNaN(d.getTime())
      ? String(slot.slot_date ?? "")
      : `${String(d.getMonth() + 1).padStart(2, "0")}/${String(
          d.getDate()
        ).padStart(2, "0")}（${DAYS_LABEL[d.getDay()]}）`;
    return slot.slot_label ? `${dateStr} ${slot.slot_label}` : dateStr;
  };

  const selectClass = (disabled) =>
    `w-40 py-1 rounded border-gray-300 text-sm text-center ${
      disabled ? "bg-gray-100 text-gray-500 cursor-not-allowed" : ""
    }`;

  return (
    <div className="min-h-screen bg-gray-200">
      {makingDraft && (
        <div className="fixed inset-0 bg-white/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="p-4 rounded-xl border bg-white shadow">
            <div className="animate-spin w-5 h-5 border-2 border-blue-200 border-t-blue-600 rounded-full mx-auto mb-3"></div>
            <div className="text-sm">事業所向けメールの下書きを作成中…</div>
          </div>
        </div>
      )}

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

      {/* Main content */}
      <main className="max-w-5xl mx-auto px-4 py-6">
        <div className="py-2">
          <button
            type="button"
            onClick={handleBack}
            className="flex items-center px-3 py-2 gap-1 rounded bg-blue-600 text-white text-sm hover:bg-blue-700"
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
        {!loading && pageErr && (
          <div className="p-6 rounded-md bg-white border shadow-sm">
            <div className="text-red-600 text-sm">{pageErr}</div>
          </div>
        )}

        {/* Content */}
        {!loading && !pageErr && data && (
          <>
            {/* 基本情報 */}
            <div className="bg-white border rounded shadow-sm p-4">
              <h1 className="text-base font-medium text-gray-700">基本情報</h1>
              <hr className="my-3 border-gray-200" />
              <dl className="divide-y">
                {/* 事業所名 */}
                <div className="flex items-center py-2">
                  <dt className="w-36 text-xs text-gray-600">事業所名</dt>
                  <dd className="flex-1 text-sm">
                    {data.session?.facility?.notion_url ? (
                      <a
                        className="text-blue-700 hover:underline"
                        href={data.session.facility.notion_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {data.session.facility.name}
                      </a>
                    ) : (
                      <span className="text-gray-900">{data.session.facility.name}</span>
                    )}
                  </dd>
                </div>

                {/* 事業所担当者 */}
                <div className="flex items-center py-2">
                  <dt className="w-36 text-xs text-gray-600">事業所担当者</dt>
                  <dd className="flex-1 text-sm">
                    {data.session.facility.contact_name || data.session.facility.contact_email ? (
                      `${data.session.facility.contact_name || ""}${
                        data.session.facility.contact_email
                          ? `（${data.session.facility.contact_email}）`
                          : ""
                      }`
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </dd>
                </div>

                {/* 評価者 */}
                <div className="flex items-center py-2">
                  <dt className="w-36 text-xs text-gray-600 leading-7">評価者</dt>
                  <dd className="flex-1 text-sm">
                    {Array.isArray(data.evaluators) && data.evaluators.length ? (
                      <ul className="space-y-1">
                        {data.evaluators.map((e, index) => (
                          <li key={e.id ?? `evaluator-${index}`} className="leading-6">
                            <div className="flex flex-wrap items-center gap-2">
                              <span>
                                {e.name}
                                {e.email ? `（${e.email}）` : ""}－
                              </span>
                              <span className="text-sm">
                                {e.form_view_url ? (
                                  <a
                                    href={e.form_view_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-blue-700 hover:underline"
                                  >
                                    確認用
                                  </a>
                                ) : (
                                  <span className="text-gray-400">確認用 —</span>
                                )}
                                <span className="mx-1">/</span>
                                {e.form_edit_url ? (
                                  <a
                                    href={e.form_edit_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-blue-700 hover:underline"
                                  >
                                    編集用
                                  </a>
                                ) : (
                                  <span className="text-gray-400">編集用 —</span>
                                )}
                              </span>
                            </div>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </dd>
                </div>

                {/* 調査目的（編集） */}
                <div className="flex items-center py-2">
                  <dt className="w-36 text-xs text-gray-600">調査目的</dt>
                  <dd className="flex-1">
                    <select
                      className="w-36 rounded border-gray-300 py-1 text-sm"
                      value={purpose}
                      onChange={(e) => setPurpose(e.target.value)}
                    >
                      {PURPOSE_OPTIONS.map((p) => (
                        <option key={p} value={p}>
                          {p}
                        </option>
                      ))}
                    </select>
                  </dd>
                </div>

                {/* 評価者回答期限（編集・インラインエラー） */}
                <div className="flex items-start py-2 gap-3">
                  <dt className="w-36 text-xs text-gray-600 mt-2">評価者回答期限</dt>
                  <dd className="flex-1">
                    <input
                      type="date"
                      className="w-36 rounded border-gray-300 py-1 text-sm"
                      value={responseDeadline || ""}
                      onChange={(e) => setResponseDeadline(e.target.value)}
                    />
                    {showDateErrors && responseDateError && (
                      <div className="text-xs text-red-600 mt-1">{responseDateError}</div>
                    )}
                  </dd>
                </div>

                {/* 事業所提示期限（編集・インラインエラー） */}
                <div className="flex items-start py-2 gap-3">
                  <dt className="w-36 text-xs text-gray-600 mt-2">事業所提示期限</dt>
                  <dd className="flex-1">
                    <input
                      type="date"
                      className="w-36 rounded border-gray-300 py-1 text-sm"
                      value={presentationDate || ""}
                      onChange={(e) => setPresentationDate(e.target.value)}
                    />
                    {showDateErrors && presentationDateError && (
                      <div className="text-xs text-red-600 mt-1">{presentationDateError}</div>
                    )}
                  </dd>
                </div>
              </dl>

              {/* 保存ボタン */}
              <div className="pt-3 flex justify-start">
                <button
                  type="button"
                  onClick={handleUpdateSession}
                  disabled={saving}
                  className={`px-3 py-2 rounded text-sm text-white ${
                    saving
                      ? "bg-blue-300 cursor-not-allowed"
                      : "bg-blue-600 hover:bg-blue-700"
                  }`}
                >
                  保存
                </button>
              </div>
            </div>

            {/* 日程調整状況 */}
            <div className="bg-white border rounded shadow-sm p-4 mt-6">
              <h2 className="text-base font-medium text-gray-700">日程調整状況</h2>
              <hr className="my-3 border-gray-200" />
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr className="[&>th]:px-2 [&>th]:py-2">
                      <th className="w-40 text-left">回答日</th>
                      <th className="w-24 text-center">事業所提案</th>
                      {data.evaluators.map((e) => (
                        <th key={e.id} className="min-w-40 text-center">
                          <div>{e.name}</div>
                          <div className="text-xs text-gray-500">
                            {formatAnsweredAt(e.answered_at)}
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {data.slots.map((slot) => {
                      const rowLocked = !!proposed[slot.id];
                      return (
                        <tr key={slot.id} className="[&>td]:px-2 [&>td]:py-2">
                          {/* 候補日時 */}
                          <td className="whitespace-nowrap text-left">
                            {formatSlot(slot)}
                          </td>
                          {/* 事業所提案（checkbox） */}
                          <td className="text-center">
                            <input
                              type="checkbox"
                              className="h-4 w-4"
                              checked={!!proposed[slot.id]}
                              onChange={(ev) =>
                                handleProposedCheck(slot.id, ev.target.checked)
                              }
                              title="全員が「○」の場合のみチェックできます"
                            />
                          </td>
                          {/* 評価者ごとの回答 */}
                          {data.evaluators.map((e) => {
                            const key = `${e.id}_${slot.id}`;
                            const v = getAns(e.id, slot.id);
                            return (
                              <td key={key} className="text-center">
                                <select
                                  className={selectClass(rowLocked)}
                                  value={v}
                                  disabled={rowLocked}
                                  onChange={(ev) =>
                                    setAns(e.id, slot.id, ev.target.value)
                                  }
                                >
                                  <option value="">ー</option>
                                  <option value="O">{TOKEN_TO_SYMBOL.O}</option>
                                  <option value="M">{TOKEN_TO_SYMBOL.M}</option>
                                  <option value="X">{TOKEN_TO_SYMBOL.X}</option>
                                </select>
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                    {/* 備考 */}
                    <tr className="[&>td]:px-2 [&>td]:py-2">
                      <td className="text-gray-700">備考</td>
                      <td></td>
                      {data.evaluators.map((e) => (
                        <td key={`note_${e.id}`} className="text-center">
                          <input
                            className="w-40 rounded border border-gray-300 text-sm px-2 py-1"
                            value={notes[e.id] ?? ""}
                            onChange={(ev) =>
                              setNotes((m) => ({ ...m, [e.id]: ev.target.value }))
                            }
                            placeholder="備考を入力"
                          />
                        </td>
                      ))}
                    </tr>
                    {/* 備考 保存ボタン（各評価者） */}
                    <tr className="[&>td]:px-2 [&>td]:py-2">
                      <td></td>
                      <td></td>
                      {data.evaluators.map((e) => (
                        <td key={`save_${e.id}`} className="text-center">
                          <button
                            type="button"
                            onClick={() => handleUpdateEvaluatorResponse(e.id)}
                            disabled={saving}
                            className={`px-3 py-2 text-white text-sm rounded ${
                              saving
                                ? "bg-blue-300 cursor-not-allowed"
                                : "bg-blue-600 hover:bg-blue-700"
                            }`}
                          >
                            保存
                          </button>
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>

              {inlineErr ? (
                <div className="mt-3 text-xs text-red-600">{inlineErr}</div>
              ) : null}

              <div className="mt-4 flex justify-start">
                <button
                  type="button"
                  onClick={handleMakeFacilityEmailDraft}
                  disabled={makingDraft || !hasProposedSelected}
                  className={`px-4 py-2 text-white text-sm rounded ${
                    makingDraft || !hasProposedSelected
                      ? "bg-blue-300 cursor-not-allowed"
                      : "bg-blue-600 hover:bg-blue-700"
                  }`}
                  title={hasProposedSelected ? "Make経由でGmail下書きを作成" : "候補にチェックすると有効になります"}
                >
                  事業所向けメール作成
                </button>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
