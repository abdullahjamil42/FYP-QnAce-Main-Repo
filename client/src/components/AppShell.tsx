"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import type { User } from "@supabase/supabase-js";
import {
  clearLoginMarker,
  getSupabaseClient,
  loginAgeMs,
  SESSION_MAX_AGE_MS,
} from "@/lib/supabase";
import BrandLogo from "@/components/BrandLogo";
import BackButton from "@/components/BackButton";
import Footer from "@/components/Footer";

type AppShellProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  actions?: ReactNode;
  showBackButton?: boolean;
  backHref?: string;
};

const navItems = [
  { label: "Home", href: "/" },
  { label: "Setup", href: "/setup" },
  { label: "Session", href: "/session/lobby" },
  { label: "Dashboard", href: "/dashboard" },
  { label: "History", href: "/history" },
  { label: "Practice", href: "/practice" },
  { label: "Reports", href: "/reports" },
  { label: "Settings", href: "/settings" },
  { label: "Help", href: "/help" },
  { label: "About", href: "/about" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function AppShell({
  title,
  subtitle,
  children,
  actions,
  showBackButton = true,
  backHref = "/",
}: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    const client = getSupabaseClient();
    if (!client) {
      return;
    }

    let mounted = true;

    client.auth.getUser().then((res: { data: { user: User | null }; error: unknown }) => {
      if (mounted) {
        setUser(res.data.user ?? null);
      }
    });

    const {
      data: { subscription },
    } = client.auth.onAuthStateChange((_event: unknown, session: any) => {
      setUser(session?.user ?? null);
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  // Close mobile nav whenever the route changes.
  useEffect(() => {
    setMobileNavOpen(false);
    setMenuOpen(false);
  }, [pathname]);

  // Lock body scroll when the mobile drawer is open.
  useEffect(() => {
    if (typeof document === "undefined") return;
    if (mobileNavOpen) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = prev;
      };
    }
  }, [mobileNavOpen]);

  // 24-hour absolute logout watchdog. Catches users who keep a tab open
  // without navigating (which would otherwise miss the middleware check).
  useEffect(() => {
    const client = getSupabaseClient();
    if (!client) return;

    let cancelled = false;

    async function checkExpiry() {
      if (cancelled) return;
      const age = loginAgeMs();
      if (age !== null && age > SESSION_MAX_AGE_MS) {
        cancelled = true;
        clearLoginMarker();
        try {
          await client!.auth.signOut();
        } catch {
          // ignore — we redirect regardless
        }
        router.replace("/login?reason=expired");
      }
    }

    void checkExpiry();
    const interval = window.setInterval(() => void checkExpiry(), 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [router]);

  const profileLabel = useMemo(() => {
    const fullName = user?.user_metadata?.full_name;
    if (typeof fullName === "string" && fullName.trim()) {
      return fullName;
    }
    return user?.email ?? "Profile";
  }, [user]);

  const initials = useMemo(() => {
    const base = profileLabel.trim();
    if (!base) {
      return "U";
    }
    const parts = base.split(/\s+/).filter(Boolean);
    if (parts.length === 1) {
      return parts[0].slice(0, 2).toUpperCase();
    }
    return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
  }, [profileLabel]);

  async function handleSignOut() {
    const client = getSupabaseClient();
    if (!client) {
      return;
    }
    await client.auth.signOut();
    clearLoginMarker();
    setMenuOpen(false);
    router.push("/login");
  }

  // Hide back button on the home page (nothing to go back to in-app).
  const shouldShowBack = showBackButton && pathname !== "/";

  return (
    <div className="app-liquid-page relative flex min-h-screen flex-col overflow-hidden text-qace-text">
      <div className="app-liquid-bg" />
      <div className="app-aurora-drift" />
      <div className="app-floating-orbs" />
      <div className="app-starfield" />
      <div className="app-liquid-noise" />
      <div className="app-vignette-breath" />

      <div className="shell-corner-glow-a pointer-events-none absolute -left-24 top-0 h-80 w-80 rounded-full bg-sky-500 blur-3xl" />
      <div className="shell-corner-glow-b pointer-events-none absolute -right-20 top-32 h-72 w-72 rounded-full bg-purple-500 blur-3xl" />
      <div className="shell-corner-glow-a pointer-events-none absolute -bottom-24 left-1/2 h-72 w-72 -translate-x-1/2 rounded-full bg-sky-400 blur-3xl" />

      <header className="sticky top-0 z-30">
        <div className="mx-auto flex w-full max-w-[92rem] items-center justify-between gap-3 px-3 py-3 sm:px-5 sm:py-4 md:px-8">
          <Link href="/" className="flex shrink-0 items-center gap-2">
            <BrandLogo className="h-7 w-auto text-white sm:h-8" />
            <span className="text-lg font-semibold tracking-tight text-white sm:text-xl">
              Q&A<span className="text-sky-400">ce</span>
            </span>
          </Link>

          <nav className="hidden items-center gap-1 overflow-x-auto rounded-full border border-white/20 bg-white/10 px-2 py-1 backdrop-blur-md xl:flex">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`whitespace-nowrap rounded-full px-3 py-1.5 text-sm transition ${
                  isActive(pathname, item.href)
                    ? "bg-white/18 text-white"
                    : "text-qace-muted hover:bg-white/10 hover:text-white"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="flex shrink-0 items-center gap-2">
            {user ? (
              <div className="relative hidden sm:block">
                <button
                  onClick={() => setMenuOpen((open) => !open)}
                  className="flex items-center gap-2 rounded-full px-2 py-1.5 text-sm text-white transition hover:text-sky-200"
                  aria-label="Open profile menu"
                >
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-qace-primary text-xs font-semibold text-white">
                    {initials}
                  </span>
                  <span className="hidden max-w-28 truncate pr-2 md:inline">
                    {profileLabel}
                  </span>
                </button>
                {menuOpen ? (
                  <div className="app-frosted absolute right-0 top-12 w-56 rounded-xl p-2">
                    <p className="px-2 py-1 text-xs text-qace-muted">Signed in as</p>
                    <p className="truncate px-2 pb-2 text-sm text-white">{user.email}</p>
                    <Link
                      href="/settings"
                      onClick={() => setMenuOpen(false)}
                      className="block w-full rounded-lg px-3 py-2 text-left text-sm text-white transition hover:bg-white/10"
                    >
                      Profile & Settings
                    </Link>
                    <button
                      onClick={handleSignOut}
                      className="w-full rounded-lg px-3 py-2 text-left text-sm text-red-200 transition hover:bg-red-500/20"
                    >
                      Sign out
                    </button>
                  </div>
                ) : null}
              </div>
            ) : (
              <Link
                href="/login"
                className="hidden rounded-full px-4 py-2 text-sm font-medium text-white transition hover:text-sky-200 sm:inline-block"
              >
                Login
              </Link>
            )}

            <button
              type="button"
              onClick={() => setMobileNavOpen((open) => !open)}
              className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/20 bg-white/10 text-white backdrop-blur-md transition hover:bg-white/15 xl:hidden"
              aria-label={mobileNavOpen ? "Close menu" : "Open menu"}
              aria-expanded={mobileNavOpen}
            >
              {mobileNavOpen ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Mobile drawer */}
      {mobileNavOpen ? (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm xl:hidden"
            onClick={() => setMobileNavOpen(false)}
            aria-hidden="true"
          />
          <aside
            className="fixed right-0 top-0 z-50 flex h-full w-[88vw] max-w-sm flex-col gap-2 overflow-y-auto border-l border-white/15 bg-[#0a0d18]/95 px-4 py-5 backdrop-blur-xl xl:hidden"
            role="dialog"
            aria-modal="true"
          >
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-[0.2em] text-white/60">
                Navigation
              </span>
              <button
                type="button"
                onClick={() => setMobileNavOpen(false)}
                className="flex h-8 w-8 items-center justify-center rounded-full border border-white/15 text-white"
                aria-label="Close menu"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>

            {user ? (
              <div className="mb-3 rounded-2xl border border-white/15 bg-white/5 p-3">
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-full bg-qace-primary text-sm font-semibold text-white">
                    {initials}
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-white">{profileLabel}</p>
                    <p className="truncate text-xs text-qace-muted">{user.email}</p>
                  </div>
                </div>
              </div>
            ) : null}

            <nav className="flex flex-col gap-1">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`rounded-xl px-3 py-2.5 text-sm transition ${
                    isActive(pathname, item.href)
                      ? "bg-white/15 text-white"
                      : "text-white/80 hover:bg-white/10 hover:text-white"
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            </nav>

            <div className="mt-auto border-t border-white/10 pt-4">
              {user ? (
                <button
                  onClick={handleSignOut}
                  className="w-full rounded-xl bg-red-500/15 px-3 py-2.5 text-sm font-medium text-red-200 transition hover:bg-red-500/25"
                >
                  Sign out
                </button>
              ) : (
                <Link
                  href="/login"
                  className="block w-full rounded-xl bg-qace-primary px-3 py-2.5 text-center text-sm font-semibold text-white transition hover:bg-indigo-400"
                >
                  Login
                </Link>
              )}
            </div>
          </aside>
        </>
      ) : null}

      <main className="relative z-10 mx-auto w-full max-w-[92rem] flex-1 px-3 py-6 sm:px-5 sm:py-8 md:px-8 md:py-12">
        {shouldShowBack ? (
          <div className="mb-4 sm:mb-5">
            <BackButton fallbackHref={backHref} />
          </div>
        ) : null}

        <section className="mb-6 flex flex-col justify-between gap-4 sm:mb-8 md:flex-row md:items-end">
          <div className="space-y-2">
            <h1 className="animate-fade-up text-2xl font-semibold sm:text-3xl md:text-4xl">
              {title}
            </h1>
            {subtitle ? (
              <p className="animate-fade-up-delayed max-w-2xl text-sm text-qace-muted sm:text-base">
                {subtitle}
              </p>
            ) : null}
          </div>
          {actions ? <div className="animate-fade-up-delayed-2">{actions}</div> : null}
        </section>
        {children}
      </main>

      <Footer variant="app" />
    </div>
  );
}
