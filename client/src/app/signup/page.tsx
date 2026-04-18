"use client";

import Link from "next/link";
import { ChangeEvent, FormEvent, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import AuthSplitLayout from "@/components/AuthSplitLayout";
import { getSupabaseClient, hasSupabaseEnv } from "@/lib/supabase";

const CV_BUCKET = "cvs";
const MAX_CV_MB = 5;

export default function SignupPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleCvChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    if (!file) return;
    if (file.type !== "application/pdf") {
      setError("CV must be a PDF file.");
      event.target.value = "";
      return;
    }
    if (file.size > MAX_CV_MB * 1024 * 1024) {
      setError(`CV must be smaller than ${MAX_CV_MB} MB.`);
      event.target.value = "";
      return;
    }
    setError(null);
    setCvFile(file);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setError(null);

    if (!cvFile) {
      setError("Please upload your CV/resume (PDF) to continue.");
      return;
    }

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

    // 1. Create the account
    const { data: authData, error: authError } = await client.auth.signUp({
      email,
      password,
      options: { data: { full_name: fullName } },
    });

    if (authError || !authData.user) {
      setLoading(false);
      setError(authError?.message ?? "Account creation failed.");
      return;
    }

    const userId = authData.user.id;
    const cvPath = `${userId}/resume.pdf`;

    // 2. Upload CV to Supabase Storage
    const { error: uploadError } = await client.storage
      .from(CV_BUCKET)
      .upload(cvPath, cvFile, { contentType: "application/pdf", upsert: true });

    if (uploadError) {
      setLoading(false);
      setError(`CV upload failed: ${uploadError.message}`);
      return;
    }

    // 3. Get public URL and store in user metadata
    const { data: urlData } = client.storage.from(CV_BUCKET).getPublicUrl(cvPath);
    await client.auth.updateUser({
      data: {
        cv_url: urlData.publicUrl,
        cv_filename: cvFile.name,
        cv_uploaded_at: new Date().toISOString(),
      },
    });

    setLoading(false);
    setMessage("Account created. If email confirmation is enabled, please verify your inbox.");
    setTimeout(() => router.push("/login"), 900);
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

        {/* CV Upload — required */}
        <div>
          <label className="mb-1 block text-sm text-qace-muted">
            CV / Resume <span className="text-red-400">*</span>
          </label>
          <div
            onClick={() => fileInputRef.current?.click()}
            className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-5 text-sm transition ${
              cvFile
                ? "border-emerald-500/60 bg-emerald-500/10 text-emerald-300"
                : "border-white/20 bg-black/20 text-qace-muted hover:border-qace-accent/60 hover:text-white"
            }`}
          >
            {cvFile ? (
              <>
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="max-w-full truncate font-medium">{cvFile.name}</span>
                <span className="text-xs opacity-70">Click to replace</span>
              </>
            ) : (
              <>
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                <span>Click to upload your CV (PDF, max {MAX_CV_MB} MB)</span>
              </>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={handleCvChange}
          />
        </div>

        {error ? <p className="text-sm text-red-300">{error}</p> : null}
        {message ? <p className="text-sm text-emerald-300">{message}</p> : null}
        <button
          type="submit"
          disabled={loading || !cvFile}
          className="w-full rounded-lg bg-qace-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:opacity-60"
        >
          {loading ? "Creating account..." : "Create Account"}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-qace-muted">
        Already have an account? <Link href="/login" className="text-qace-accent">Sign in</Link>
      </p>
    </AuthSplitLayout>
  );
}
