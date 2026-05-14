import { createBrowserClient } from "@supabase/ssr";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

let cachedClient: ReturnType<typeof createBrowserClient> | null = null;

export function getSupabaseClient() {
  if (!supabaseUrl || !supabaseAnonKey) {
    return null;
  }

  if (!cachedClient) {
    // createBrowserClient stores the session in cookies (not localStorage),
    // so the server-side middleware can read it and avoid redirect loops.
    cachedClient = createBrowserClient(supabaseUrl, supabaseAnonKey);
  }

  return cachedClient;
}

export function hasSupabaseEnv() {
  return Boolean(supabaseUrl && supabaseAnonKey);
}

const LOGIN_AT_COOKIE = "qace_login_at";
const TWENTY_FOUR_HOURS_S = 24 * 60 * 60;

/** Stamp the moment the user signed in. Read by middleware + AppShell watchdog
 *  to enforce a hard 24-hour absolute session lifetime. */
export function markLoginNow() {
  if (typeof document === "undefined") return;
  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  document.cookie =
    `${LOGIN_AT_COOKIE}=${Date.now()}; Max-Age=${TWENTY_FOUR_HOURS_S}; Path=/; SameSite=Lax${secure}`;
}

/** Wipe the login-timestamp cookie. Called on sign-out or expiry. */
export function clearLoginMarker() {
  if (typeof document === "undefined") return;
  document.cookie = `${LOGIN_AT_COOKIE}=; Max-Age=0; Path=/; SameSite=Lax`;
}

/** Returns ms since login, or null if cookie absent / unparseable. */
export function loginAgeMs(): number | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie
    .split(";")
    .map((c) => c.trim())
    .find((c) => c.startsWith(`${LOGIN_AT_COOKIE}=`));
  if (!match) return null;
  const value = match.split("=")[1];
  const ts = Number(value);
  if (!Number.isFinite(ts)) return null;
  return Date.now() - ts;
}

export const SESSION_MAX_AGE_MS = TWENTY_FOUR_HOURS_S * 1000;
