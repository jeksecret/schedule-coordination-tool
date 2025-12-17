import { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session ?? null);
      setLoading(false);
    });

    const { data: sub } = supabase.auth.onAuthStateChange((_evt, sess) => {
      setSession(sess ?? null);
    });

    return () => sub.subscription.unsubscribe();
  }, []);

  const getAccessToken = async () => {
    let { data } = await supabase.auth.getSession();
    let s = data?.session ?? null;

    const now = Math.floor(Date.now() / 1000);
    const exp = s?.expires_at ?? 0;

    if (!s || (exp && exp - now <= 30)) {
      const { data: ref } = await supabase.auth.refreshSession();
      s = ref?.session ?? null;
      setSession(s ?? null);
    }
    return s?.access_token ?? null;
  };

  const signInWithGoogle = async () => {
    const redirectTo = `${window.location.origin}/auth/callback`;
    await supabase.auth.signInWithOAuth({ provider: "google", options: { redirectTo } });
  };

  const signOut = async () => {
    await supabase.auth.signOut();
    window.location.replace("/login?e=signedout");
  };

  const value = {
    session,
    user: session?.user ?? null,
    loading,
    getAccessToken,
    signInWithGoogle,
    signOut,
  };

  if (loading) {
    return <div className="min-h-screen grid place-items-center text-gray-500">Loading…</div>;
  }

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  return useContext(AuthCtx);
}
