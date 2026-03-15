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
      <div className="app-liquid-noise" />

      <div className="shell-corner-glow-a pointer-events-none absolute -left-24 top-0 h-80 w-80 rounded-full bg-qace-primary/20 blur-3xl" />
      <div className="shell-corner-glow-b pointer-events-none absolute -right-20 top-32 h-72 w-72 rounded-full bg-qace-accent/20 blur-3xl" />

      <header className="app-frosted sticky top-0 z-20 border-b">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-4 py-4 md:px-8">
          <Link href="/" className="flex items-center">
            <BrandLogo className="h-8 w-auto text-white" />
          </Link>
          <nav className="hidden items-center gap-2 md:flex">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-full px-3 py-1.5 text-sm transition ${
                  isActive(pathname, item.href)
                    ? "app-frosted-soft text-white"
                    : "text-qace-muted hover:bg-white/10 hover:text-white"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
          {user ? (
            <div className="relative">
              <button
                onClick={() => setMenuOpen((open) => !open)}
                className="app-frosted-soft flex items-center gap-2 rounded-full px-2 py-1.5 text-sm text-white transition hover:bg-white/12"
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
              className="app-frosted-soft rounded-full px-4 py-2 text-sm font-medium text-white transition hover:bg-white/12"
            >
              Login
            </Link>
          )}
        </div>
        <div className="mx-auto w-full max-w-7xl overflow-x-auto px-4 pb-3 md:hidden md:px-8">
          <nav className="flex min-w-max items-center gap-2">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-full px-3 py-1.5 text-sm transition ${
                  isActive(pathname, item.href)
                    ? "app-frosted-soft text-white"
                    : "text-qace-muted hover:bg-white/10 hover:text-white"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>

      <main className="relative z-10 mx-auto w-full max-w-7xl px-4 py-10 md:px-8 md:py-12">
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
