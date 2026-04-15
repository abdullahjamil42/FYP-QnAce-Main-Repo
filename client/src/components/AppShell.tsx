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
    <div className="relative min-h-screen overflow-hidden text-qace-text selection:bg-[var(--accent-hover)] selection:text-white bg-black">
      <div className="apple-gradient-bg" />

      <header className="sticky top-0 z-50 w-full apple-glass border-x-0 border-t-0 bg-transparent mb-8">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-3">
          <Link href="/" className="flex items-center gap-2 group">
            <BrandLogo className="h-6 w-auto text-white transition-transform group-hover:scale-105" />
            <span className="text-lg font-semibold tracking-tight text-white">
              Q&A<span className="text-[var(--accent-base)] font-bold">ce</span>
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-1.5 py-1 backdrop-blur-md">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`whitespace-nowrap rounded-full px-4 py-1.5 text-xs font-medium transition-all ${
                  isActive(pathname, item.href)
                    ? "bg-white/10 text-white shadow-sm"
                    : "text-[var(--muted)] hover:bg-white/5 hover:text-white"
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
                className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 pl-2 pr-4 py-1.5 text-xs font-semibold text-white transition hover:bg-white/10"
              >
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[var(--accent-base)] text-[10px] text-white">
                  {initials}
                </span>
                <span className="max-w-28 truncate">{profileLabel}</span>
              </button>
              {menuOpen ? (
                <div className="absolute right-0 mt-3 w-56 rounded-2xl apple-glass p-2 shadow-2xl">
                  <div className="px-3 py-2 border-b border-white/10 mb-2">
                    <p className="text-[10px] uppercase tracking-wider text-[var(--muted)]">Signed in as</p>
                    <p className="truncate text-sm font-medium text-white">{user.email}</p>
                  </div>
                  <button
                    onClick={handleSignOut}
                    className="w-full rounded-xl px-3 py-2 text-left text-xs font-semibold text-red-400 transition hover:bg-red-500/10"
                  >
                    Sign out
                  </button>
                </div>
              ) : null}
            </div>
          ) : (
            <Link
              href="/login"
              className="apple-btn-secondary text-xs"
            >
              Login
            </Link>
          )}
        </div>
      </header>

      <main className="relative z-10 mx-auto w-full max-w-7xl px-6 pb-24">
        <section className="mb-10 flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
          <div className="space-y-1">
            <h1 className="animate-fade-up text-3xl font-bold tracking-tight md:text-4xl">{title}</h1>
            {subtitle ? <p className="animate-fade-up-delayed max-w-2xl text-sm text-[var(--muted)]">{subtitle}</p> : null}
          </div>
          {actions ? <div className="animate-fade-up-delayed-2 shrink-0">{actions}</div> : null}
        </section>
        <div className="animate-fade-up-delayed">{children}</div>
      </main>
    </div>
  );
}
