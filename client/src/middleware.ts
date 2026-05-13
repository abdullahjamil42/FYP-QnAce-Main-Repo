import { NextRequest, NextResponse } from "next/server";
import { createServerClient, type CookieOptions } from "@supabase/ssr";

const PUBLIC_PATHS = new Set<string>([
  "/",
  "/login",
  "/signup",
  "/about",
  "/help",
  "/auth/callback",
  "/forgot-password",
  "/reset-password",
]);

const TWENTY_FOUR_HOURS_MS = 24 * 60 * 60 * 1000;

function isPublic(pathname: string): boolean {
  if (PUBLIC_PATHS.has(pathname)) return true;
  if (pathname.startsWith("/_next/")) return true;
  if (pathname.startsWith("/api/")) return true;
  if (pathname === "/favicon.ico") return true;
  if (/\.(svg|png|jpg|jpeg|gif|webp|ico|css|js|map|txt|woff2?)$/i.test(pathname)) {
    return true;
  }
  return false;
}

export async function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;

  if (isPublic(pathname)) {
    return NextResponse.next();
  }

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    // No auth configured — fail closed in production, open in dev
    if (process.env.NODE_ENV === "production") {
      const url = req.nextUrl.clone();
      url.pathname = "/login";
      url.search = `?next=${encodeURIComponent(pathname + search)}`;
      return NextResponse.redirect(url);
    }
    return NextResponse.next();
  }

  const response = NextResponse.next();

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

  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.search = `?next=${encodeURIComponent(pathname + search)}`;
    return NextResponse.redirect(url);
  }

  // Absolute 24-hour lifetime check (in addition to Supabase token expiry)
  const loginAtRaw = req.cookies.get("qace_login_at")?.value;
  const loginAt = loginAtRaw ? Number(loginAtRaw) : NaN;
  if (Number.isFinite(loginAt) && Date.now() - loginAt > TWENTY_FOUR_HOURS_MS) {
    // Server-side hard logout: clear Supabase auth cookies + our marker
    await supabase.auth.signOut();
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.search = `?reason=expired&next=${encodeURIComponent(pathname + search)}`;
    const redirect = NextResponse.redirect(url);
    redirect.cookies.set({
      name: "qace_login_at",
      value: "",
      maxAge: 0,
      path: "/",
    });
    return redirect;
  }

  return response;
}

export const config = {
  matcher: [
    // Run on every path except static assets and Next internals.
    // Public-vs-protected logic is handled inside the middleware body.
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
