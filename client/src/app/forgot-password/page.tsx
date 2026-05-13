"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import AuthSplitLayout from "@/components/AuthSplitLayout";
import { getSupabaseClient, hasSupabaseEnv } from "@/lib/supabase";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
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
      setError("Could not initialise authentication client.");
      return;
    }

    setLoading(true);
    const { error: authError } = await client.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/callback?type=recovery`,
    });
    setLoading(false);

    if (authError) {
      setError(authError.message);
      return;
    }

    setSent(true);
  }

  return (
    <AuthSplitLayout
      mode="login"
      title="Reset Password"
      subtitle="Enter your email address and we'll send you a reset link."
    >
      {sent ? (
        <div className="space-y-4">
          <div className="rounded-lg border border-emerald-300/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
            Password reset email sent. Check your inbox and follow the link to set a new password.
          </div>
          <p className="text-center text-sm text-qace-muted">
            <Link href="/login" className="text-qace-accent hover:underline">
              Back to login
            </Link>
          </p>
        </div>
      ) : (
        <>
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="mb-1 block text-sm text-qace-muted">Email address</label>
              <input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full rounded-lg border border-white/15 bg-black/20 px-3 py-2 text-sm outline-none transition focus:border-qace-accent"
              />
            </div>
            {error ? <p className="text-sm text-red-300">{error}</p> : null}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-qace-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:opacity-60"
            >
              {loading ? "Sending..." : "Send Reset Link"}
            </button>
          </form>
          <p className="mt-4 text-center text-sm text-qace-muted">
            Remembered it?{" "}
            <Link href="/login" className="text-qace-accent hover:underline">
              Sign in
            </Link>
          </p>
        </>
      )}
    </AuthSplitLayout>
  );
}
