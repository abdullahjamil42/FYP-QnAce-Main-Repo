"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { ProgressRow } from "@/components/ui";
import { listSessions, type SessionRecord } from "@/lib/interview-session-store";

export default function DashboardPage() {
  const [sessions, setSessions] = useState<SessionRecord[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const rows = await listSessions();
      if (!cancelled) {
        setSessions(rows);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const currentScore = sessions[0]?.final_score ?? 0;
  const previousScore = sessions[1]?.final_score ?? currentScore;
  const delta = currentScore - previousScore;
  const weekTrend = useMemo(
    () => sessions.slice(0, 7).map((session) => Math.max(10, Math.round(session.final_score))).reverse(),
    [sessions]
  );

  const avgContent = useMemo(() => {
    if (sessions.length === 0) {
      return 0;
    }
    return sessions.reduce((sum, item) => sum + item.content_score, 0) / sessions.length;
  }, [sessions]);

  const avgDelivery = useMemo(() => {
    if (sessions.length === 0) {
      return 0;
    }
    return sessions.reduce((sum, item) => sum + item.delivery_score, 0) / sessions.length;
  }, [sessions]);

  const avgComposure = useMemo(() => {
    if (sessions.length === 0) {
      return 0;
    }
    return sessions.reduce((sum, item) => sum + item.composure_score, 0) / sessions.length;
  }, [sessions]);

  return (
    <AppShell
      title="Progress Dashboard"
      subtitle="Track your interview growth over time and focus your next practice session on the biggest gains."
      actions={
        <Link href="/practice" className="rounded-full bg-qace-primary px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400">
          Start Targeted Practice
        </Link>
      }
    >
      <div className="card-glow animate-fade-up overflow-hidden rounded-2xl border border-white/20 bg-white/5 shadow-xl shadow-black/40 backdrop-blur-md">

        {/* Stats row */}
        <div className="grid grid-cols-1 divide-y divide-white/10 border-b border-white/10 md:grid-cols-3 md:divide-x md:divide-y-0">
          <div className="px-5 py-5">
            <p className="text-sm text-qace-muted">Current Score</p>
            <p className="mt-2 text-4xl font-semibold text-qace-accent">{currentScore.toFixed(0)}</p>
            <p className="mt-1 text-xs text-emerald-300">{delta >= 0 ? "+" : ""}{delta.toFixed(0)} vs previous session</p>
          </div>
          <div className="px-5 py-5">
            <p className="text-sm text-qace-muted">Sessions Completed</p>
            <p className="mt-2 text-4xl font-semibold">{sessions.length}</p>
            <p className="mt-1 text-xs text-qace-muted">Latest session tracked in reports and history.</p>
          </div>
          <div className="px-5 py-5">
            <p className="text-sm text-qace-muted">Best Category</p>
            <p className="mt-2 text-2xl font-semibold">
              {avgContent >= avgDelivery && avgContent >= avgComposure
                ? "Content Quality"
                : avgDelivery >= avgComposure
                  ? "Delivery"
                  : "Composure"}
            </p>
            <p className="mt-1 text-xs text-qace-muted">Computed from your saved interview sessions.</p>
          </div>
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 divide-y divide-white/10 md:grid-cols-2 md:divide-x md:divide-y-0">
          <div className="px-5 py-5">
            <h2 className="text-lg font-semibold">7-Session Trend</h2>
            <div className="mt-4 flex h-40 items-end gap-2">
              {weekTrend.map((point, idx) => (
                <div key={`${point}-${idx}`} className="flex-1 rounded-t-lg bg-gradient-to-t from-qace-primary to-qace-accent/90" style={{ height: `${point}%` }} />
              ))}
            </div>
            <p className="mt-2 text-xs text-qace-muted">Latest trajectory indicates steady upward momentum.</p>
          </div>
          <div className="px-5 py-5">
            <h2 className="mb-3 text-lg font-semibold">Focus Areas</h2>
            <div className="space-y-3">
              <ProgressRow label="Content Quality" value={avgContent} hint="Increase concrete impact metrics and sharper examples." />
              <ProgressRow label="Delivery" value={avgDelivery} hint="Use short pause control to reduce filler words." />
              <ProgressRow label="Composure" value={avgComposure} hint="Maintain eye-line and confidence in follow-up probes." />
            </div>
          </div>
        </div>

      </div>
    </AppShell>
  );
}
