import { NextRequest, NextResponse } from "next/server";
import { createServerClient, type CookieOptions } from "@supabase/ssr";

/**
 * Universal Supabase auth callback handler.
 *
 * Supabase redirects here after:
 *   1. Email verification   (type=signup or type=email) → exchange code, sign
 *      out, bounce to /login?verified=1 so the user enters password + gets
 *      the qace_login_at cookie set cleanly.
 *   2. Password reset       (type=recovery) → exchange code, KEEP session so
 *      /reset-password can call updateUser({ password }), then redirect there.
 *
 * The `?code=` parameter is the PKCE authorization code from Supabase.
 */
export async function GET(req: NextRequest) {
  const url = req.nextUrl.clone();
  const code = url.searchParams.get("code");
  const type = url.searchParams.get("type"); // "signup" | "email" | "recovery" | null
  const errorDescription = url.searchParams.get("error_description");

  const fail = (reason: string) => {
    const u = req.nextUrl.clone();
    u.pathname = "/login";
    u.search = `?reason=${reason}`;
    return NextResponse.redirect(u);
  };

  if (errorDescription) return fail("verify_failed");

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!code || !supabaseUrl || !supabaseAnonKey) return fail("verify_failed");

  // Build the response before mutating cookies
  const isRecovery = type === "recovery";
  const dest = req.nextUrl.clone();
  dest.pathname = isRecovery ? "/reset-password" : "/login";
  dest.search = isRecovery ? "" : "?verified=1";
  const response = NextResponse.redirect(dest);

  const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      get(name: string) {
        return req.cookies.get(name)?.value;
      },
      set(name: string, value: string, options: CookieOptions) {
        response.cookies.set({ name, value, ...options });
      },
      remove(name: string, options: CookieOptions) {
        response.cookies.set({ name, value: "", ...options, maxAge: 0 });
      },
    },
  });

  const { error } = await supabase.auth.exchangeCodeForSession(code);
  if (error) return fail("verify_failed");

  if (isRecovery) {
    // Keep the session — /reset-password will use it to call updateUser.
    return response;
  }

  // Email verification: sign out so they re-enter via the login form
  // (which stamps the qace_login_at cookie).
  await supabase.auth.signOut();
  return response;
}
