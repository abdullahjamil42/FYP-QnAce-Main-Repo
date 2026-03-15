"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { GlassCard, ProgressRow } from "@/components/ui";
import { getSessionById, type SessionRecord } from "@/lib/interview-session-store";

export default function ReportDetailPage({ params }: { params: { id: string } }) {
  const [session, setSession] = useState<SessionRecord | null>(null);

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
      <section className="grid gap-4 lg:grid-cols-3">
        <GlassCard className="animate-fade-up lg:col-span-2">
          <h2 className="mb-3 text-lg font-semibold">Rubric Breakdown</h2>
          <div className="space-y-3">
            {breakdown.map((metric) => (
              <ProgressRow key={metric.label} label={metric.label} value={metric.value} />
            ))}
          </div>
          <p className="mt-4 text-xs text-qace-muted">
            Session mode: <span className="capitalize text-white">{session?.mode ?? "unknown"}</span> | Difficulty: {session?.difficulty ?? "unknown"}
          </p>
        </GlassCard>

        <GlassCard className="animate-fade-up-delayed">
          <h2 className="text-lg font-semibold">Coach Notes</h2>
          <ul className="mt-3 space-y-2 text-sm text-qace-muted">
            <li>Open with a concise context statement in technical responses.</li>
            <li>Anchor each answer to measurable impact where possible.</li>
            <li>Maintain eye-line stability during complex explanations.</li>
            <li>Reduce repeated transition phrases for smoother delivery.</li>
          </ul>
        </GlassCard>
      </section>

      <section className="mt-4 grid gap-4 md:grid-cols-2">
        <GlassCard className="animate-fade-up-delayed">
          <h3 className="text-lg font-semibold">Suggested Rewrite</h3>
          <p className="mt-3 text-sm text-qace-muted">
            "I designed a cache invalidation strategy that reduced stale reads by 41% and improved API p95 latency by 120ms. I coordinated with frontend and infra teams, then monitored rollout with feature flags and fallback controls."
          </p>
        </GlassCard>

        <GlassCard className="animate-fade-up-delayed-2">
          <h3 className="text-lg font-semibold">Next Drill Plan</h3>
          <ol className="mt-3 space-y-2 text-sm text-qace-muted">
            <li>1. 10-minute behavioral response compression practice.</li>
            <li>2. Two follow-up technical scenarios with strict 90-second answers.</li>
            <li>3. Re-run full mock interview and compare composure delta.</li>
          </ol>
        </GlassCard>
      </section>
    </AppShell>
  );
}
