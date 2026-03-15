"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { GlassCard, ProgressRow } from "@/components/ui";
import { getLatestSession, getSessionById, type SessionRecord } from "@/lib/interview-session-store";

export default function SessionSummaryPage() {
  const [session, setSession] = useState<SessionRecord | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const sessionId = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("sessionId") : null;
      const next = sessionId ? await getSessionById(sessionId) : await getLatestSession();
      if (!cancelled) {
        setSession(next);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const strengths = useMemo(() => {
    if (!session) {
      return [];
    }
    const items: string[] = [];
    if (session.content_score >= 80) items.push("Strong answer structure and relevance to prompts.");
    if (session.delivery_score >= 75) items.push("Stable speaking pace and clarity under pressure.");
    if (session.composure_score >= 75) items.push("Consistent on-camera composure and eye-line control.");
    return items.length > 0 ? items : ["Good completion discipline and consistent participation."];
  }, [session]);

  const opportunities = useMemo(() => {
    if (!session) {
      return [];
    }
    const items: string[] = [];
    if (session.content_score < 75) items.push("Add more concrete metrics in each answer.");
    if (session.delivery_score < 75) items.push("Reduce filler words with shorter sentence blocks.");
    if (session.composure_score < 75) items.push("Maintain camera focus during difficult follow-ups.");
    return items.length > 0 ? items : ["Increase complexity by switching to Advanced mode next run."];
  }, [session]);

  return (
    <AppShell
      title="Session Summary"
      subtitle="A concise review of your latest interview run, with strengths and improvement points ready for action."
      actions={
        <div className="flex gap-2">
          <Link href="/reports/demo-001" className="rounded-full border border-white/20 bg-white/5 px-4 py-2 text-sm font-semibold transition hover:bg-white/10">
            Open Report
          </Link>
          <Link href="/session/live" className="rounded-full bg-qace-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400">
            Retry Session
          </Link>
        </div>
      }
    >
      <section className="grid gap-4 lg:grid-cols-3">
        <GlassCard className="animate-fade-up lg:col-span-1">
          <p className="text-sm text-qace-muted">Overall Score</p>
          <p className="mt-2 text-5xl font-semibold text-qace-accent">{session ? session.final_score.toFixed(0) : "-"}</p>
          <p className="mt-2 text-sm text-qace-muted">
            Mode: <span className="capitalize">{session?.mode ?? "-"}</span> · Duration: {session?.duration_minutes ?? "-"}m
          </p>
        </GlassCard>

        <GlassCard className="animate-fade-up-delayed lg:col-span-2">
          <h2 className="mb-3 text-lg font-semibold">Dimension Scores</h2>
          <div className="space-y-3">
            <ProgressRow label="Content Quality" value={session?.content_score ?? 0} hint="Measures relevance and structure quality." />
            <ProgressRow label="Delivery" value={session?.delivery_score ?? 0} hint="Measures pace, clarity, and communication polish." />
            <ProgressRow label="Composure" value={session?.composure_score ?? 0} hint="Measures confidence and non-verbal steadiness." />
          </div>
        </GlassCard>
      </section>

      <section className="mt-4 grid gap-4 md:grid-cols-2">
        <GlassCard className="animate-fade-up-delayed">
          <h3 className="text-lg font-semibold">Strengths</h3>
          <ul className="mt-3 space-y-2 text-sm text-qace-muted">
            {strengths.map((item) => (
              <li key={item}>• {item}</li>
            ))}
          </ul>
        </GlassCard>

        <GlassCard className="animate-fade-up-delayed-2">
          <h3 className="text-lg font-semibold">Opportunities</h3>
          <ul className="mt-3 space-y-2 text-sm text-qace-muted">
            {opportunities.map((item) => (
              <li key={item}>• {item}</li>
            ))}
          </ul>
        </GlassCard>
      </section>
    </AppShell>
  );
}
