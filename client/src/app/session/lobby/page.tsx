"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { Badge, GlassCard } from "@/components/ui";
import { fetchBackendHealth } from "@/lib/backend";
import { loadSetupConfig } from "@/lib/interview-session-store";

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

  useEffect(() => {
    setSetup(loadSetupConfig());
  }, []);

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
            <p className="mt-2 text-qace-muted">Mode: <span className="text-white capitalize">{setup.mode}</span></p>
            <p className="text-qace-muted">Difficulty: <span className="text-white">{setup.difficulty}</span></p>
            <p className="text-qace-muted">Duration: <span className="text-white">{setup.durationMinutes} min</span></p>
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
