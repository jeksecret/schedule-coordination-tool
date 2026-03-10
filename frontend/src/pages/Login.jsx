import { useAuth } from "../context/AuthContext";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function Login() {
  const { signInWithGoogle, user, loading } = useAuth();
  const nav = useNavigate();
  const err = new URLSearchParams(window.location.search).get("e");

  useEffect(() => {
    if (!loading && user) {
      nav("/session/list", { replace: true });
    }
  }, [user, loading, nav]);

  return (
    <div className="min-h-screen bg-gray-200 grid place-items-center px-4">
      <div className="w-full max-w-md bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <h1 className="text-base font-semibold mb-4">社内ログイン</h1>
        <p className="text-sm text-gray-500">Googleアカウントでログインしてください。</p>

        {err === "domain" && (
          <div className="mt-2 mb-4 text-xs text-red-600">
            このサービスは社内アカウントのみ利用できます。
            <br />
            <span className="font-medium">@smartworx.co.jp、</span>
            <span className="font-medium">@nabepero.co.jp、</span>または{" "}
            <span className="font-medium">@cio-sw.com</span> のメールでログインしてください。
          </div>
        )}

        {err === "signedout" && (
          <div className="mt-2 mb-4 text-xs text-red-600">
            ログアウトしました。再度ログインしてください。
          </div>
        )}

        <button
          onClick={signInWithGoogle}
          className="w-full flex items-center justify-center gap-3 border border-gray-200 rounded px-4 py-2.5 hover:bg-gray-50 mt-4"
        >
          <img
            src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg"
            alt="Google logo"
            className="w-5 h-5"
          />
          <span className="text-sm text-gray-700">Googleでログイン</span>
        </button>
      </div>
    </div>
  );
}
