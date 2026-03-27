"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import AuthSplitLayout from "@/components/AuthSplitLayout";
import { getSupabaseClient, hasSupabaseEnv } from "@/lib/supabase";

export default function SignupPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
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
    const { error: authError } = await client.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: fullName,
        },
      },
    });
    setLoading(false);

    if (authError) {
      setError(authError.message);
      return;
    }

    setMessage("Account created. If email confirmation is enabled, please verify your inbox.");
    setTimeout(() => {
      router.push("/login");
    }, 900);
  }

  return (
    <AuthSplitLayout
      mode="signup"
      title="Create Account"
      subtitle="Set up your profile to save sessions, unlock trends, and receive personalized interview coaching."
    >
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div>
          <label className="mb-1 block text-sm text-qace-muted">Full Name</label>
          <input
            type="text"
            placeholder="Your name"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            required
            className="w-full rounded-lg border border-white/15 bg-black/20 px-3 py-2 text-sm outline-none transition focus:border-qace-accent"
          />
        </div>
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
            placeholder="Create a password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={8}
            required
            className="w-full rounded-lg border border-white/15 bg-black/20 px-3 py-2 text-sm outline-none transition focus:border-qace-accent"
          />
        </div>
        {error ? <p className="text-sm text-red-300">{error}</p> : null}
        {message ? <p className="text-sm text-emerald-300">{message}</p> : null}
        <button type="submit" disabled={loading} className="w-full rounded-lg bg-qace-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:opacity-60">
          {loading ? "Creating account..." : "Create Account"}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-qace-muted">
        Already have an account? <Link href="/login" className="text-qace-accent">Sign in</Link>
      </p>
    </AuthSplitLayout>
  );
}
