"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import { GlassCard } from "@/components/ui";
import { getSupabaseClient, hasSupabaseEnv } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!hasSupabaseEnv()) {
      setError("Supabase environment variables are missing.");
      return;
    }

    const client = getSupabaseClient();
    if (!client) {
      setError("Supabase client could not be initialized.");
      return;
    }

    setLoading(true);
    const { error: authError } = await client.auth.signInWithPassword({
      email,
      password,
    });
    setLoading(false);

    if (authError) {
      setError(authError.message);
      return;
    }

    router.push("/setup");
  }

  return (
    <AppShell title="Welcome Back" subtitle="Sign in to access your interview history, personalized reports, and progress analytics.">
      <div className="mx-auto w-full max-w-md">
        <GlassCard className="animate-fade-up">
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="mb-1 block text-sm text-qace-muted">Email</label>
              <input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                className="w-full rounded-lg border border-white/15 bg-black/20 px-3 py-2 text-sm outline-none transition focus:border-qace-accent"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-qace-muted">Password</label>
              <input
                type="password"
                placeholder="********"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                className="w-full rounded-lg border border-white/15 bg-black/20 px-3 py-2 text-sm outline-none transition focus:border-qace-accent"
              />
            </div>
            {error ? <p className="text-sm text-red-300">{error}</p> : null}
            <button type="submit" disabled={loading} className="w-full rounded-lg bg-qace-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:opacity-60">
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>
          <p className="mt-4 text-center text-sm text-qace-muted">
            New here? <Link href="/signup" className="text-qace-accent">Create account</Link>
          </p>
        </GlassCard>
      </div>
    </AppShell>
  );
}
