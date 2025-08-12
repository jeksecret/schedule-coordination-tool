import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "../lib/supabase";

export default function AuthCallback() {
  const nav = useNavigate();

  useEffect(() => {
    // Supabase handles the code in URL; getSession will be set shortly
    const timer = setTimeout(async () => {
      const { data } = await supabase.auth.getSession();
      if (data.session) {
        nav("/dashboard", { replace: true });
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
