"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AuthSplitLayout from "@/components/AuthSplitLayout";
import { getSupabaseClient } from "@/lib/supabase";

export default function ResetPasswordPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionReady, setSessionReady] = useState(false);

  // The /auth/callback route already exchanged the code and set the session
  // cookies before redirecting here. We just confirm there is a live session.
  useEffect(() => {
    const client = getSupabaseClient();
    if (!client) return;
    client.auth.getSession().then(({ data }: { data: { session: unknown }; error: unknown }) => {
      if (data.session) {
        setSessionReady(true);
      } else {
        // No session — the link was invalid or already used.
        router.replace("/login?reason=verify_failed");
      }
    });
  }, [router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    const client = getSupabaseClient();
    if (!client) return;

    setLoading(true);
    const { error: updateError } = await client.auth.updateUser({ password });
    setLoading(false);

    if (updateError) {
      setError(updateError.message);
      return;
    }

    // Sign out so they log in fresh and qace_login_at gets stamped.
    await client.auth.signOut();
    router.push("/login?reason=password_reset");
  }

  if (!sessionReady) {
    return (
      <AuthSplitLayout
        mode="login"
        title="Reset Password"
        subtitle="Verifying your reset link…"
      >
        <p className="text-center text-sm text-qace-muted">Please wait…</p>
      </AuthSplitLayout>
    );
  }

  return (
    <AuthSplitLayout
      mode="login"
      title="Set New Password"
      subtitle="Choose a strong password — at least 8 characters."
    >
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div>
          <label className="mb-1 block text-sm text-qace-muted">New password</label>
          <input
            type="password"
            placeholder="Min 8 characters"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            className="w-full rounded-lg border border-white/15 bg-black/20 px-3 py-2 text-sm outline-none transition focus:border-qace-accent"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-qace-muted">Confirm new password</label>
          <input
            type="password"
            placeholder="Repeat password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
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
          {loading ? "Updating…" : "Update Password"}
        </button>
      </form>
    </AuthSplitLayout>
  );
}
