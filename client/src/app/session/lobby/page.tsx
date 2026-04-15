"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { Badge, GlassCard } from "@/components/ui";
import { fetchBackendHealth } from "@/lib/backend";
import { loadSetupConfig, saveSetupConfig } from "@/lib/interview-session-store";

const checks = [
  { name: "Camera", value: "Ready", tone: "success" as const },
  { name: "Microphone", value: "Ready", tone: "success" as const },
  { name: "Network", value: "Stable 24ms", tone: "success" as const },
  { name: "Noise Level", value: "Moderate", tone: "warning" as const },
];

export default function SessionLobbyPage() {
  const [setup, setSetup] = useState(loadSetupConfig());
  const [healthState, setHealthState] = useState<"checking" | "online" | "offline">("checking");
  const [models, setModels] = useState<Record<string, string | null>>({});
  const [cvUploading, setCvUploading] = useState(false);
  const [cvParsedInfo, setCvParsedInfo] = useState<any>(null);

  useEffect(() => {
    setSetup(loadSetupConfig());
  }, []);

  const updateSetup = (key: string, value: any) => {
    const newSetup = { ...setup, [key]: value };
    setSetup(newSetup);
    saveSetupConfig(newSetup);
  };

  const handleCvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setCvUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    
    try {
      const backendUrl = process.env.NEXT_PUBLIC_QACE_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${backendUrl}/api/cv/upload`, {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        updateSetup("cvSessionId", data.cv_session_id);
        setCvParsedInfo(data.parsed_cv);
      } else {
        console.error("Failed to upload CV");
      }
    } catch (err) {
      console.error(err);
    } finally {
      setCvUploading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    async function run() {
      const health = await fetchBackendHealth();
      if (cancelled) {
        return;
      }
      if (!health) {
        setHealthState("offline");
        return;
      }
      setHealthState("online");
      setModels(health.models || {});
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  const modelEntries = useMemo(() => Object.entries(models), [models]);

  return (
    <AppShell
      title="Session Lobby"
      subtitle="Run your pre-flight checks and enter the live interview room with confidence."
      actions={
        <Link
          href="/session/live"
          className="rounded-full bg-qace-primary px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400"
        >
          Enter Live Room
        </Link>
      }
    >
      <section className="grid gap-4 md:grid-cols-2">
        <GlassCard className="animate-fade-up">
          <h2 className="text-lg font-semibold">Device Readiness</h2>
          <p className="mt-1 text-sm text-qace-muted">Validate your setup before starting to avoid interruptions.</p>
          <div className="mt-4 space-y-2">
            {checks.map((check) => (
              <div key={check.name} className="flex items-center justify-between rounded-xl bg-black/20 px-3 py-2">
                <span className="text-sm text-qace-muted">{check.name}</span>
                <Badge tone={check.tone}>{check.value}</Badge>
              </div>
            ))}
          </div>

          <div className="card-glow mt-5 rounded-xl border border-white/10 bg-black/20 p-3 text-sm">
            <p className="text-xs uppercase tracking-wide text-qace-muted">Session Setup</p>
            <p className="mt-2 text-qace-muted">Mode: <span className="text-white capitalize font-semibold">{setup.mode}</span></p>
            <p className="text-qace-muted">Difficulty: <span className="text-white font-semibold">{setup.difficulty}</span></p>
            <p className="text-qace-muted">Duration: <span className="text-white font-semibold">{setup.durationMinutes} min</span></p>

            <div className="mt-5 border-t border-white/10 pt-4">
              <label className="mb-2 block text-xs font-semibold text-qace-muted">Stress Simulation Level</label>
              <div className="grid grid-cols-2 gap-2">
                {["none", "mild", "high", "brutal"].map((level) => (
                  <button
                    key={level}
                    onClick={() => updateSetup("stressLevel", level)}
                    className={`rounded-xl p-2.5 text-left text-xs transition-all duration-300 ${
                      (setup.stressLevel || "none") === level
                        ? "border border-qace-primary bg-qace-primary/20 text-white shadow-[0_0_12px_rgba(56,189,248,0.35)]"
                        : "bg-black/40 border-transparent border text-slate-400 hover:bg-black/60"
                    }`}
                  >
                    <span className="block font-semibold capitalize">{level}</span>
                    <span className="mt-0.5 block opacity-70">
                      {level === "none" && "Standard Mode"}
                      {level === "mild" && "Professional/Demanding"}
                      {level === "high" && "Curt/Confrontational"}
                      {level === "brutal" && "Relentless pressure"}
                    </span>
                  </button>
                ))}
              </div>
              {(setup.stressLevel === "high" || setup.stressLevel === "brutal") && (
                <p className="mt-3 text-xs text-red-400/90 flex items-center gap-1.5 bg-red-500/10 p-2 rounded-lg border border-red-500/20">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                  Warning: Intentional mid-utterance interrupts active.
                </p>
              )}
            </div>

            <div className="mt-5 border-t border-white/10 pt-4">
              <label className="mb-2 block text-xs font-semibold text-qace-muted">Context & Experience</label>
              <div className={`relative rounded-xl border border-dashed transition-all duration-300 p-4 text-center ${cvUploading ? 'border-qace-primary bg-qace-primary/10' : cvParsedInfo ? 'border-green-500/30 bg-green-500/5' : 'border-white/20 bg-black/20 hover:bg-black/40 hover:border-white/40'}`}>
                <input
                  type="file"
                  accept=".pdf,.docx,.txt"
                  onChange={handleCvUpload}
                  disabled={cvUploading}
                  className="absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0"
                />
                {!cvUploading && !cvParsedInfo && (
                  <>
                    <svg className="mx-auto mb-2 h-6 w-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
                    <p className="text-xs text-slate-300">Drop CV or Resume here</p>
                    <p className="mt-0.5 text-[10px] text-slate-500">PDF, DOCX up to 5MB</p>
                  </>
                )}
                {cvUploading && (
                  <div className="flex flex-col items-center gap-2">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-qace-primary border-t-transparent" />
                    <p className="text-xs text-qace-primary">Extracting Skills...</p>
                  </div>
                )}
                {cvParsedInfo && !cvUploading && (
                  <div className="text-left">
                    <div className="flex items-center gap-2 mb-2">
                      <svg className="h-5 w-5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                      <span className="text-xs font-semibold text-green-400">Identity Embedded</span>
                    </div>
                    <p className="text-xs text-slate-300 truncate"><span className="opacity-60">Candidate:</span> {cvParsedInfo.name}</p>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {(cvParsedInfo.skills || []).slice(0, 4).map((s: string) => (
                        <span key={s} className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] text-slate-300">{s}</span>
                      ))}
                      {(cvParsedInfo.skills?.length > 4) && <span className="text-[10px] text-slate-500">+{cvParsedInfo.skills.length - 4} more</span>}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </GlassCard>

        <GlassCard className="animate-fade-up-delayed">
          <h2 className="text-lg font-semibold">Session Notes</h2>
          <ul className="mt-3 space-y-2 text-sm text-qace-muted">
            <li>Keep your camera at eye level and maintain natural eye contact.</li>
            <li>Use concise STAR structure for behavioral prompts.</li>
            <li>Pause before answering to improve clarity and confidence score.</li>
            <li>Tap "Enter Live Room" once your environment is quiet.</li>
          </ul>
          <div className="mt-5 rounded-xl border border-qace-accent/30 bg-qace-accent/10 p-3 text-sm text-qace-text">
            Expected latency budget: under 800ms per turn in normal network conditions.
          </div>
          <div className="card-glow mt-3 rounded-xl border border-white/10 bg-black/20 p-3 text-xs text-qace-muted">
            <div className="mb-2 flex items-center justify-between">
              <span>Backend Status</span>
              <Badge tone={healthState === "online" ? "success" : "warning"}>
                {healthState === "checking" ? "Checking" : healthState}
              </Badge>
            </div>
            {modelEntries.length === 0 ? (
              <p>No model details available yet.</p>
            ) : (
              <div className="grid grid-cols-2 gap-1">
                {modelEntries.map(([key, value]) => (
                  <span key={key}>
                    {key}: {value ? "ready" : "n/a"}
                  </span>
                ))}
              </div>
            )}
          </div>
        </GlassCard>
      </section>
    </AppShell>
  );
}
