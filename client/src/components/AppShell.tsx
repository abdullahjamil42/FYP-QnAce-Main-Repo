"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import type { User } from "@supabase/supabase-js";
import { getSupabaseClient } from "@/lib/supabase";
import BrandLogo from "@/components/BrandLogo";

type AppShellProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  actions?: ReactNode;
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

export default function AppShell({ title, subtitle, children, actions }: AppShellProps) {
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const client = getSupabaseClient();
    if (!client) {
      return;
    }

    let mounted = true;

    client.auth.getUser().then(({ data }) => {
      if (mounted) {
        setUser(data.user ?? null);
      }
    });

    const {
      data: { subscription },
    } = client.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

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
    setMenuOpen(false);
  }

  return (
    <div className="app-liquid-page relative min-h-screen overflow-hidden text-qace-text">
      <div className="app-liquid-bg" />
      <div className="app-aurora-drift" />
      <div className="app-floating-orbs" />
      <div className="app-starfield" />
      <div className="app-liquid-noise" />
      <div className="app-vignette-breath" />

      <div className="shell-corner-glow-a pointer-events-none absolute -left-24 top-0 h-80 w-80 rounded-full bg-sky-500 blur-3xl" />
      <div className="shell-corner-glow-b pointer-events-none absolute -right-20 top-32 h-72 w-72 rounded-full bg-purple-500 blur-3xl" />
      <div className="shell-corner-glow-a pointer-events-none absolute -bottom-24 left-1/2 h-72 w-72 -translate-x-1/2 rounded-full bg-sky-400 blur-3xl" />

      <header className="sticky top-0 z-20">
        <div className="mx-auto grid w-full max-w-[92rem] grid-cols-[1fr_auto_1fr] items-center gap-3 px-3 py-4 sm:px-5 md:px-8">
          <Link href="/" className="justify-self-start flex items-center gap-2">
            <BrandLogo className="h-8 w-auto text-white" />
            <span className="text-xl font-semibold tracking-tight text-white">
              Q&A<span className="text-sky-400">ce</span>
            </span>
          </Link>

          <nav className="justify-self-center flex max-w-[56vw] items-center gap-1 overflow-x-auto rounded-full border border-white/20 bg-white/10 px-2 py-1 backdrop-blur-md">
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

          {user ? (
            <div className="relative justify-self-end">
              <button
                onClick={() => setMenuOpen((open) => !open)}
                className="flex items-center gap-2 rounded-full px-2 py-1.5 text-sm text-white transition hover:text-sky-200"
              >
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-qace-primary text-xs font-semibold text-white">
                  {initials}
                </span>
                <span className="max-w-28 truncate pr-2">{profileLabel}</span>
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
              className="justify-self-end rounded-full px-4 py-2 text-sm font-medium text-white transition hover:text-sky-200"
            >
              Login
            </Link>
          )}
        </div>
      </header>

      <main className="relative z-10 mx-auto w-full max-w-[92rem] px-3 py-10 sm:px-5 md:px-8 md:py-12">
        <section className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div className="space-y-2">
            <h1 className="animate-fade-up text-3xl font-semibold md:text-4xl">{title}</h1>
            {subtitle ? <p className="animate-fade-up-delayed max-w-2xl text-qace-muted">{subtitle}</p> : null}
          </div>
          {actions ? <div className="animate-fade-up-delayed-2">{actions}</div> : null}
        </section>
        {children}
      </main>
    </div>
  );
}
