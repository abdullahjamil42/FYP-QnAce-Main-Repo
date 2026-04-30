"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { Badge } from "@/components/ui";
import { listSessions, type SessionRecord } from "@/lib/interview-session-store";

export default function HistoryPage() {
  const [sessions, setSessions] = useState<SessionRecord[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const items = await listSessions();
      if (!cancelled) {
        setSessions(items);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <AppShell
      title="Practice History"
      subtitle="Review previous interview sessions, compare progress, and reopen detailed reports for each run."
      actions={
        <Link href="/session/live" className="rounded-full bg-qace-primary px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400">
          New Session
        </Link>
      }
    >
      <div className="card-glow animate-fade-up overflow-hidden rounded-2xl border border-white/20 bg-white/5 shadow-xl shadow-black/40 backdrop-blur-md">
        <table className="w-full text-left text-sm">
          <thead className="bg-white/5 text-qace-muted">
            <tr>
              <th className="px-4 py-3 font-medium">Session ID</th>
              <th className="px-4 py-3 font-medium">Date</th>
              <th className="px-4 py-3 font-medium">Mode</th>
              <th className="px-4 py-3 font-medium">Score</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Action</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((item) => (
              <tr key={item.id} className="border-t border-white/10">
                <td className="px-4 py-3 font-mono text-xs text-qace-muted">{item.id.slice(0, 8)}</td>
                <td className="px-4 py-3">{new Date(item.created_at).toLocaleDateString()}</td>
                <td className="px-4 py-3">{item.mode}</td>
                <td className="px-4 py-3 font-semibold">{item.final_score.toFixed(0)}</td>
                <td className="px-4 py-3">
                  <Badge tone={item.final_score < 70 ? "warning" : "success"}>{item.status}</Badge>
                </td>
                <td className="px-4 py-3">
                  <Link href={`/reports/${item.id}`} className="text-qace-accent transition hover:text-sky-200">
                    Open Report
                  </Link>
                </td>
              </tr>
            ))}
            {sessions.length === 0 ? (
              <tr>
                <td className="px-4 py-5 text-sm text-qace-muted" colSpan={6}>
                  No sessions yet. Start your first interview from the live session page.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </AppShell>
  );
}
