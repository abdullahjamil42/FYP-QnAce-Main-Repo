"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { listSessions, type SessionRecord } from "@/lib/interview-session-store";

export default function ReportsPage() {
  const [sessions, setSessions] = useState<SessionRecord[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const entries = await listSessions();
      if (!cancelled) {
        setSessions(entries);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <AppShell
      title="Feedback Reports"
      subtitle="Open detailed report views to inspect scoring rationale, delivery metrics, and concrete improvement suggestions."
    >
      <div className="card-glow animate-fade-up overflow-hidden rounded-2xl border border-white/20 bg-white/5 shadow-xl shadow-black/40 backdrop-blur-md">
        {sessions.length === 0 ? (
          <div className="px-5 py-5">
            <p className="text-sm text-qace-muted">No reports yet. Complete a live interview session to generate your first report.</p>
          </div>
        ) : (
          sessions.map((session, index) => (
            <div key={session.id} className={index < sessions.length - 1 ? "border-b border-white/10 px-5 py-5" : "px-5 py-5"}>
              <p className="text-xs uppercase tracking-wide text-qace-muted">Report</p>
              <h2 className="mt-1 text-lg font-semibold">{session.id.slice(0, 8)}</h2>
              <p className="mt-2 text-sm text-qace-muted">
                {session.mode} · {session.difficulty} · Final score {session.final_score.toFixed(0)}
              </p>
              <Link href={`/reports/${session.id}`} className="mt-4 inline-flex rounded-lg bg-white/10 px-3 py-2 text-sm font-medium transition hover:bg-white/15">
                View Details
              </Link>
            </div>
          ))
        )}
      </div>
    </AppShell>
  );
}
