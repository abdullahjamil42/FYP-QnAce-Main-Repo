"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import AppShell from "@/components/AppShell";
import { GlassCard } from "@/components/ui";
import { getSupabaseClient } from "@/lib/supabase";
import type { User } from "@supabase/supabase-js";

const CV_BUCKET = "CV";
const MAX_CV_MB = 5;

function CvSection({ user }: { user: User | null }) {
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState<{ type: "success" | "error"; msg: string } | null>(null);
  const [existingCvUrl, setExistingCvUrl] = useState<string | null>(null);
  const [existingCvName, setExistingCvName] = useState<string>("resume.pdf");
  const [uploadedAt, setUploadedAt] = useState<string | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load CV info from user_profiles table
  useEffect(() => {
    if (!user) { setProfileLoading(false); return; }
    const client = getSupabaseClient();
    if (!client) { setProfileLoading(false); return; }
    void client
      .from("user_profiles")
      .select("cv_url, cv_filename, cv_uploaded_at")
      .eq("id", user.id)
      .single()
      .then(({ data }) => {
        if (data) {
          setExistingCvUrl(data.cv_url ?? null);
          setExistingCvName(data.cv_filename ?? "resume.pdf");
          setUploadedAt(data.cv_uploaded_at ?? null);
        }
        setProfileLoading(false);
      });
  }, [user]);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    if (!file) return;
    if (file.type !== "application/pdf") {
      setStatus({ type: "error", msg: "CV must be a PDF file." });
      event.target.value = "";
      return;
    }
    if (file.size > MAX_CV_MB * 1024 * 1024) {
      setStatus({ type: "error", msg: `CV must be smaller than ${MAX_CV_MB} MB.` });
      event.target.value = "";
      return;
    }
    setStatus(null);
    setCvFile(file);
  }

  async function handleUpload() {
    if (!cvFile || !user) return;
    const client = getSupabaseClient();
    if (!client) return;

    setUploading(true);
    setStatus(null);

    const cvPath = `${user.id}/resume.pdf`;
    const { error: uploadError } = await client.storage
      .from(CV_BUCKET)
      .upload(cvPath, cvFile, { contentType: "application/pdf", upsert: true });

    if (uploadError) {
      setUploading(false);
      setStatus({ type: "error", msg: `Upload failed: ${uploadError.message}` });
      return;
    }

    const { data: urlData } = client.storage.from(CV_BUCKET).getPublicUrl(cvPath);
    const now = new Date().toISOString();

    // Update user_profiles table (source of truth)
    await client.from("user_profiles").upsert({
      id: user.id,
      cv_path: cvPath,
      cv_url: urlData.publicUrl,
      cv_filename: cvFile.name,
      cv_uploaded_at: now,
    });

    setUploading(false);
    setCvFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    setExistingCvUrl(urlData.publicUrl);
    setExistingCvName(cvFile.name);
    setUploadedAt(now);
    setStatus({ type: "success", msg: "CV updated successfully." });
  }

  return (
    <GlassCard className="animate-fade-up col-span-full">
      <h2 className="text-lg font-semibold">CV / Resume</h2>
      <p className="mt-1 text-sm text-qace-muted">Your CV is used to personalise interview coaching and question selection.</p>

      {/* Current CV */}
      {profileLoading ? (
        <div className="mt-4 h-14 animate-pulse rounded-lg bg-white/5" />
      ) : existingCvUrl ? (
        <div className="mt-4 flex items-center gap-3 rounded-lg border border-white/10 bg-black/20 px-4 py-3">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 flex-shrink-0 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-white">{existingCvName}</p>
            {uploadedAt ? (
              <p className="text-xs text-qace-muted">
                Uploaded {new Date(uploadedAt).toLocaleDateString(undefined, { dateStyle: "medium" })}
              </p>
            ) : null}
          </div>
          <a
            href={existingCvUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg border border-white/15 px-3 py-1.5 text-xs text-white transition hover:bg-white/10"
          >
            View
          </a>
        </div>
      ) : (
        <p className="mt-3 text-sm text-amber-300">No CV uploaded yet.</p>
      )}

      {/* Upload new CV */}
      <div className="mt-4">
        <p className="mb-2 text-sm text-qace-muted">{existingCvUrl ? "Replace CV:" : "Upload CV:"}</p>
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
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="max-w-full truncate font-medium">{cvFile.name}</span>
              <span className="text-xs opacity-70">Click to choose a different file</span>
            </>
          ) : (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              <span>Click to select a PDF (max {MAX_CV_MB} MB)</span>
            </>
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={handleFileChange}
        />

        {cvFile ? (
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="mt-3 w-full rounded-lg bg-qace-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:opacity-60"
          >
            {uploading ? "Uploading..." : existingCvUrl ? "Replace CV" : "Upload CV"}
          </button>
        ) : null}

        {status ? (
          <p className={`mt-2 text-sm ${ status.type === "success" ? "text-emerald-300" : "text-red-300" }`}>
            {status.msg}
          </p>
        ) : null}
      </div>
    </GlassCard>
  );
}

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const client = getSupabaseClient();
    if (!client) return;
    client.auth.getUser().then(({ data }) => setUser(data.user ?? null));
    const { data: { subscription } } = client.auth.onAuthStateChange((_e, session) => {
      setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  return (
    <AppShell
      title="Profile & Preferences"
      subtitle="Personalize your interview prep defaults, feedback behavior, and privacy controls."
    >
      <section className="grid gap-4 md:grid-cols-2">
        {/* CV Section — spans full width */}
        <CvSection user={user} />

        <GlassCard className="animate-fade-up">
          <h2 className="text-lg font-semibold">Interview Defaults</h2>
          <div className="mt-4 space-y-3 text-sm text-qace-muted">
            <label className="flex items-center justify-between rounded-lg bg-black/20 px-3 py-2">
              <span>Default mode</span>
              <span className="text-white">Technical</span>
            </label>
            <label className="flex items-center justify-between rounded-lg bg-black/20 px-3 py-2">
              <span>Session length</span>
              <span className="text-white">20 minutes</span>
            </label>
            <label className="flex items-center justify-between rounded-lg bg-black/20 px-3 py-2">
              <span>Difficulty</span>
              <span className="text-white">Standard</span>
            </label>
          </div>
        </GlassCard>

        <GlassCard className="animate-fade-up-delayed">
          <h2 className="text-lg font-semibold">Device & Privacy</h2>
          <div className="mt-4 space-y-3 text-sm text-qace-muted">
            <label className="flex items-center justify-between rounded-lg bg-black/20 px-3 py-2">
              <span>Camera preview in lobby</span>
              <input type="checkbox" defaultChecked className="h-4 w-4 accent-qace-primary" />
            </label>
            <label className="flex items-center justify-between rounded-lg bg-black/20 px-3 py-2">
              <span>Store session transcripts</span>
              <input type="checkbox" defaultChecked className="h-4 w-4 accent-qace-primary" />
            </label>
            <label className="flex items-center justify-between rounded-lg bg-black/20 px-3 py-2">
              <span>Email performance digest</span>
              <input type="checkbox" className="h-4 w-4 accent-qace-primary" />
            </label>
          </div>
        </GlassCard>
      </section>
    </AppShell>
  );
}
