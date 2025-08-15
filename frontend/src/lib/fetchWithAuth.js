import { supabase } from "./supabase";

async function getAccessToken() {
  const { data } = await supabase.auth.getSession();
  return data?.session?.access_token ?? null;
}

function defaultRedirect(href) {
  if (typeof window !== "undefined" && window.location?.replace) {
    window.location.replace(href);
  }
}

export async function fetchWithAuth(url, options = {}) {
  const token = await getAccessToken();
  if (!token) throw new Error("No session/token available");

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
    Authorization: `Bearer ${token}`,
  };

  return fetch(url, { credentials: "include", ...options, headers });
}

export async function fetchWithAuthJson(url, options = {}) {
  const { onForbidden, onUnauthorized, ...fetchOpts } = options;
  const res = await fetchWithAuth(url, fetchOpts);

  if (res.ok) {
    const text = await res.text().catch(() => "");
    if (!text) return {};
    try {
      return JSON.parse(text);
    } catch {
      return { raw: text };
    }
  }

  const status = res.status;
  const text = await res.text().catch(() => "");

  if (status === 403) {
    if (typeof onForbidden === "function") {
      onForbidden({ status, text, url });
    } else {
      defaultRedirect("/login?e=domain");
    }
    return;
  }

  if (status === 401) {
    if (typeof onUnauthorized === "function") {
      onUnauthorized({ status, text, url });
    } else {
      defaultRedirect("/login");
    }
    return;
  }

  throw new Error(`HTTP ${status} ${text}`);
}
