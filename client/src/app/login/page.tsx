"use client";

import Link from "next/link";
import { FormEvent, Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import AuthSplitLayout from "@/components/AuthSplitLayout";
import { getSupabaseClient, hasSupabaseEnv, markLoginNow } from "@/lib/supabase";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const expired = searchParams.get("reason") === "expired";
  const verified = searchParams.get("verified") === "1";
  const verifyFailed = searchParams.get("reason") === "verify_failed";
  const passwordReset = searchParams.get("reason") === "password_reset";
  const nextPath = searchParams.get("next") || "/setup";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resendLoading, setResendLoading] = useState(false);
  const [resendSent, setResendSent] = useState(false);

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
      // Supabase returns "Email not confirmed" for unverified accounts when
      // "Confirm email" is enabled in the dashboard — surface it with a resend option.
      if (authError.message.toLowerCase().includes("email not confirmed")) {
        setError("email_not_confirmed");
      } else {
        setError(authError.message);
      }
      return;
    }

    markLoginNow();

    const safeNext =
      nextPath.startsWith("/") && !nextPath.startsWith("//")
        ? nextPath
        : "/setup";
    router.push(safeNext);
  }

  async function handleResendVerification() {
    const client = getSupabaseClient();
    if (!client || !email) return;
    setResendLoading(true);
    await client.auth.resend({
      type: "signup",
      email,
      options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
    });
    setResendLoading(false);
    setResendSent(true);
  }

  return (
    <AuthSplitLayout
      mode="login"
      title="Welcome Back"
      subtitle="Sign in to access your interview history, personalized reports, and progress analytics."
    >
      {expired ? (
        <div className="mb-4 rounded-lg border border-amber-300/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
          Your session expired after 24 hours. Please sign in again to continue.
        </div>
      ) : null}
      {verified ? (
        <div className="mb-4 rounded-lg border border-emerald-300/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
          Email verified. You can now sign in.
        </div>
      ) : null}
      {passwordReset ? (
        <div className="mb-4 rounded-lg border border-emerald-300/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
          Password updated successfully. Sign in with your new password.
        </div>
      ) : null}
      {verifyFailed ? (
        <div className="mb-4 rounded-lg border border-red-300/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
          Verification link is invalid or has expired. Please try again.
        </div>
      ) : null}
      {error === "email_not_confirmed" ? (
        <div className="mb-4 rounded-lg border border-amber-300/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
          <p className="font-medium">Email not verified yet.</p>
          <p className="mt-1 text-xs">
            Check your inbox for the confirmation link we sent when you signed up.
          </p>
          {resendSent ? (
            <p className="mt-2 text-xs text-emerald-300">
              Verification email resent — check your inbox.
            </p>
          ) : (
            <button
              type="button"
              onClick={handleResendVerification}
              disabled={resendLoading}
              className="mt-2 text-xs underline hover:no-underline disabled:opacity-60"
            >
              {resendLoading ? "Sending…" : "Resend verification email"}
            </button>
          )}
        </div>
      ) : null}
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
          <div className="mb-1 flex items-center justify-between">
            <label className="text-sm text-qace-muted">Password</label>
            <Link href="/forgot-password" className="text-xs text-qace-accent hover:underline">
              Forgot password?
            </Link>
          </div>
          <input
            type="password"
            placeholder="********"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            className="w-full rounded-lg border border-white/15 bg-black/20 px-3 py-2 text-sm outline-none transition focus:border-qace-accent"
          />
        </div>
        {error && error !== "email_not_confirmed" ? (
          <p className="text-sm text-red-300">{error}</p>
        ) : null}
        <button type="submit" disabled={loading} className="w-full rounded-lg bg-qace-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:opacity-60">
          {loading ? "Signing in..." : "Sign In"}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-qace-muted">
        New here? <Link href="/signup" className="text-qace-accent">Create account</Link>
      </p>
    </AuthSplitLayout>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
