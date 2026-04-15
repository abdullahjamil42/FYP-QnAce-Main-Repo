"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { GlassCard, ProgressRow } from "@/components/ui";
import { getSessionById, type SessionRecord } from "@/lib/interview-session-store";

export default function ReportDetailPage({ params }: { params: { id: string } }) {
  const [session, setSession] = useState<SessionRecord | null>(null);
  const [coaching, setCoaching] = useState<any>(null);
  const [isLoadingCoaching, setIsLoadingCoaching] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const item = await getSessionById(params.id);
      if (!cancelled) {
        setSession(item);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  useEffect(() => {
    if (!session) return;
    const activeSession = session;
    let cancelled = false;
    
    async function fetchCoaching() {
      setIsLoadingCoaching(true);
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${apiUrl}/api/report/${params.id}/coaching`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            transcripts: activeSession.transcript_events || [],
            scores: { final: activeSession.final_score },
            stress_level: activeSession.stress_level || "none",
            mode: activeSession.mode
          })
        });
        if (!res.ok) throw new Error("Failed to fetch coaching");
        const data = await res.json();
        if (!cancelled) setCoaching(data);
      } catch (err) {
        console.error("Coaching fetch failed:", err);
      } finally {
        if (!cancelled) setIsLoadingCoaching(false);
      }
    }
    
    fetchCoaching();
    return () => { cancelled = true; };
  }, [session]);

  const breakdown = useMemo(
    () => [
      { label: "Content Quality", value: session?.content_score ?? 0 },
      { label: "Delivery", value: session?.delivery_score ?? 0 },
      { label: "Composure", value: session?.composure_score ?? 0 },
      { label: "Vocal Confidence", value: session?.latest_perception?.acoustic_confidence ? session.latest_perception.acoustic_confidence * 100 : 0 },
      { label: "Facial Engagement", value: session?.latest_perception?.face_emotion ? 74 : 0 },
    ],
    [session]
  );

  return (
    <AppShell
      title={`Report ${params.id}`}
      subtitle="Comprehensive analysis of interview performance across content quality, delivery, and composure dimensions."
      actions={
        <Link href="/session/live" className="rounded-full bg-qace-primary px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400">
          Run Another Session
        </Link>
      }
    >
      <section className="grid gap-6 lg:grid-cols-3">
        <GlassCard className="animate-fade-up lg:col-span-2">
          <h2 className="mb-4 text-xl font-bold tracking-tight text-white">Rubric Breakdown</h2>
          <div className="space-y-3">
            {breakdown.map((metric) => (
              <ProgressRow key={metric.label} label={metric.label} value={metric.value} />
            ))}
          </div>
          <div className="mt-6 border-t border-white/10 pt-4 text-xs font-medium tracking-wide text-qace-muted/80">
            Session mode: <span className="capitalize text-white">{session?.mode ?? "unknown"}</span> • Difficulty: {session?.difficulty ?? "unknown"}
          </div>
        </GlassCard>

        <GlassCard className="animate-fade-up-delayed">
          <h2 className="mb-4 text-xl font-bold tracking-tight text-white">Coach Notes</h2>
          {isLoadingCoaching ? (
            <div className="mt-4 flex flex-col gap-3">
              <div className="h-4 w-3/4 animate-pulse rounded bg-white/10" />
              <div className="h-4 w-5/6 animate-pulse rounded bg-white/10" />
              <div className="h-4 w-2/3 animate-pulse rounded bg-white/10" />
            </div>
          ) : coaching ? (
            <div className="space-y-4 text-sm text-qace-muted">
               <div className="rounded-2xl border border-white/5 bg-black/40 p-4">
                 <strong className="text-white block mb-1">General Analysis:</strong> {coaching.general_tip}
               </div>
               {coaching.stress_tip && <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-4 shadow-[0_0_15px_rgba(239,68,68,0.1)]">
                 <strong className="text-red-400 block mb-1">Under Pressure:</strong> {coaching.stress_tip}
               </div>}
               {coaching.cv_tip && <div className="rounded-2xl border border-blue-500/20 bg-blue-500/5 p-4">
                 <strong className="text-blue-400 block mb-1">CV Alignment:</strong> {coaching.cv_tip}
               </div>}
            </div>
          ) : (
            <div className="mt-3 text-sm text-qace-muted">Not available for this session.</div>
          )}
        </GlassCard>
      </section>

      {session?.stress_level && session.stress_level !== "none" && (
        <section className="mt-6 grid gap-6 md:grid-cols-2">
          <GlassCard className="animate-fade-up-delayed md:col-span-2">
            <h3 className="mb-4 text-xl font-bold tracking-tight text-white">Stress Analytics ({session.stress_level})</h3>
            <div className="grid gap-4 text-sm text-qace-muted md:grid-cols-3">
               <div className="rounded-2xl border border-indigo-500/20 bg-indigo-500/10 p-5 shadow-[0_4px_20px_rgba(99,102,241,0.05)]">
                 <p className="font-semibold text-white tracking-wide">Composure Delta</p>
                 <p className="mt-2 text-indigo-200/80">Maintained relative calm despite sharp follow-ups.</p>
               </div>
               <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-5 shadow-[0_4px_20px_rgba(239,68,68,0.05)]">
                 <p className="font-semibold text-white tracking-wide">Interruption Response</p>
                 <p className="mt-2 text-red-200/80">Good recovery time after mid-utterance stops.</p>
               </div>
               <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-5 shadow-[0_4px_20px_rgba(16,185,129,0.05)]">
                 <p className="font-semibold text-white tracking-wide">Silence Handling</p>
                 <p className="mt-2 text-emerald-200/80">Pivoted answers confidently during dead silence.</p>
               </div>
            </div>
          </GlassCard>
        </section>
      )}

      <section className="mt-6 grid gap-6 md:grid-cols-2">
        <GlassCard className="animate-fade-up-delayed">
          <h3 className="mb-3 text-xl font-bold tracking-tight text-white">Suggested Rewrite</h3>
          <p className="mt-2 rounded-r-xl border-l-2 border-white/20 bg-white/5 px-3 py-2 text-sm italic leading-relaxed text-qace-muted">
            "I designed a cache invalidation strategy that reduced stale reads by 41% and improved API p95 latency by 120ms. I coordinated with frontend and infra teams, then monitored rollout with feature flags and fallback controls."
          </p>
        </GlassCard>

        <GlassCard className="animate-fade-up-delayed-2">
          <h3 className="mb-3 text-xl font-bold tracking-tight text-white">Next Drill Plan</h3>
          <ol className="mt-2 list-inside list-decimal space-y-3 rounded-2xl border border-white/5 bg-black/40 p-4 text-sm font-medium text-qace-muted">
            <li className="pl-1">10-minute behavioral response compression practice.</li>
            <li className="pl-1">Two follow-up technical scenarios with strict 90-second answers.</li>
            <li className="pl-1">Re-run full mock interview and compare composure delta.</li>
          </ol>
        </GlassCard>
      </section>
    </AppShell>
  );
}
