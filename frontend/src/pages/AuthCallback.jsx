import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "../lib/supabase";

export default function AuthCallback() {
  const nav = useNavigate();

  useEffect(() => {
    const hash = window.location.hash || "";
    const hashParams = new URLSearchParams(hash.replace(/^#/, ""));
    const oauthError = hashParams.get("error") || hashParams.get("error_description");
    if (oauthError) {
      nav("/login?e=domain", { replace: true });
      return;
    }

    const timer = setTimeout(async () => {
      const { data } = await supabase.auth.getSession();
      if (data.session) {
        nav("/session/list", { replace: true });
      } else {
        nav("/login", { replace: true });
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [nav]);

  return (
    <div className="min-h-screen grid place-items-center text-gray-500">
      認証処理中…
    </div>
  );
}
