"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { Badge } from "@/components/ui";
import { fetchBackendHealth } from "@/lib/backend";
import { loadSetupConfig } from "@/lib/interview-session-store";
import { jobRoles, interviewTypes } from "@/lib/mock-data";

type CheckStatus = "checking" | "ready" | "unavailable";

interface DeviceCheck {
  name: string;
  status: CheckStatus;
  detail: string;
}

export default function SessionLobbyPage() {
  const [setup, setSetup] = useState(loadSetupConfig());
  const [healthState, setHealthState] = useState<"checking" | "online" | "offline">("checking");
  const [models, setModels] = useState<Record<string, string | null>>({});
  const [checks, setChecks] = useState<DeviceCheck[]>([
    { name: "Camera", status: "checking", detail: "Checking..." },
    { name: "Microphone", status: "checking", detail: "Checking..." },
    { name: "Network", status: "checking", detail: "Checking..." },
  ]);

  useEffect(() => {
    setSetup(loadSetupConfig());
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function checkCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        stream.getTracks().forEach((t) => t.stop());
        if (!cancelled) {
          setChecks((prev) =>
            prev.map((c) => c.name === "Camera" ? { ...c, status: "ready" as const, detail: "Ready" } : c)
          );
        }
      } catch {
        if (!cancelled) {
          setChecks((prev) =>
            prev.map((c) => c.name === "Camera" ? { ...c, status: "unavailable" as const, detail: "No access" } : c)
          );
        }
      }
    }

    async function checkMicrophone() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach((t) => t.stop());
        if (!cancelled) {
          setChecks((prev) =>
            prev.map((c) => c.name === "Microphone" ? { ...c, status: "ready" as const, detail: "Ready" } : c)
          );
        }
      } catch {
        if (!cancelled) {
          setChecks((prev) =>
            prev.map((c) => c.name === "Microphone" ? { ...c, status: "unavailable" as const, detail: "No access" } : c)
          );
        }
      }
    }

    async function checkNetwork() {
      const start = performance.now();
      const health = await fetchBackendHealth();
      const ping = Math.round(performance.now() - start);
      if (cancelled) return;

      if (!health) {
        setHealthState("offline");
        setChecks((prev) =>
          prev.map((c) => c.name === "Network" ? { ...c, status: "unavailable" as const, detail: "Backend offline" } : c)
        );
        return;
      }
      setHealthState("online");
      setModels(health.models || {});
      setChecks((prev) =>
        prev.map((c) => c.name === "Network" ? { ...c, status: "ready" as const, detail: `Stable ${ping}ms` } : c)
      );
    }

    void checkCamera();
    void checkMicrophone();
    void checkNetwork();

    return () => { cancelled = true; };
  }, []);

  const modelEntries = useMemo(() => Object.entries(models), [models]);
  const allReady = checks.every((c) => c.status === "ready");
  const roleName = jobRoles.find((r) => r.id === setup.jobRole)?.title ?? setup.jobRole;
  const typeName = interviewTypes.find((t) => t.id === setup.interviewType)?.title ?? setup.interviewType;

  return (
    <AppShell
      title="Session Lobby"
      subtitle="Run your pre-flight checks and enter the live interview room with confidence."
      actions={
        <Link
          href="/session/live"
          className={`rounded-full px-5 py-2.5 text-sm font-semibold text-white transition ${allReady
              ? "bg-qace-primary hover:bg-indigo-400"
              : "pointer-events-none bg-slate-600 opacity-50"
            }`}
        >
          Enter Live Room
        </Link>
      }
    >
      <div className="card-glow animate-fade-up overflow-hidden rounded-2xl border border-white/20 bg-white/5 shadow-xl shadow-black/40 backdrop-blur-md">

        {/* Device Readiness */}
        <div className="border-b border-white/10 px-5 py-5">
          <h2 className="text-lg font-semibold">Device Readiness</h2>
          <p className="mt-1 text-sm text-qace-muted">Validate your setup before starting to avoid interruptions.</p>
          <div className="mt-4 space-y-2">
            {checks.map((check) => (
              <div key={check.name} className="flex items-center justify-between rounded-xl bg-black/20 px-3 py-2">
                <span className="text-sm text-qace-muted">{check.name}</span>
                <Badge
                  tone={
                    check.status === "ready"
                      ? "success"
                      : check.status === "unavailable"
                        ? "warning"
                        : undefined
                  }
                >
                  {check.detail}
                </Badge>
              </div>
            ))}
          </div>

          <div className="card-glow mt-5 rounded-xl border border-white/10 bg-black/20 p-3 text-sm">
            <p className="text-xs uppercase tracking-wide text-qace-muted">Interview Configuration</p>
            <p className="mt-2 text-qace-muted">Role: <span className="text-white">{roleName}</span></p>
            <p className="text-qace-muted">Format: <span className="text-white">{typeName}</span></p>
            <p className="text-qace-muted">
              Duration:{" "}
              <span className="text-white">
                {setup.durationMinutes > 0 ? `${setup.durationMinutes} min` : "Unlimited"}
              </span>
            </p>
          </div>
        </div>

        {/* Session Notes */}
        <div className="px-5 py-5">
          <h2 className="text-lg font-semibold">Session Notes</h2>
          <ul className="mt-3 space-y-2 text-sm text-qace-muted">
            <li>Keep your camera at eye level and maintain natural eye contact.</li>
            <li>Take your time — there are no time limits on thinking or answering.</li>
            <li>Two interviewers will alternate questions — stay focused during transitions.</li>
            <li>Tap &ldquo;Enter Live Room&rdquo; once your environment is quiet.</li>
          </ul>
          <div className="mt-5 rounded-xl border border-qace-accent/30 bg-qace-accent/10 p-3 text-sm text-qace-text">
            {setup.interviewType === "extensive"
              ? "Extensive mode: facial and voice emotion analysis will be active throughout."
              : "Quick mode: fast-paced 10-minute interview with focused questions."
            }
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
        </div>

      </div>
    </AppShell>
  );
}
