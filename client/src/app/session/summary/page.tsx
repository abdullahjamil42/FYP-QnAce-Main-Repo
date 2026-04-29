"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import AppShell from "@/components/AppShell";
import { GlassCard, ProgressRow } from "@/components/ui";
import { getLatestSession, getSessionById, type SessionRecord } from "@/lib/interview-session-store";
import { streamCoaching } from "@/lib/backend";
import { jobRoles } from "@/lib/mock-data";
import type { PerQuestionScore } from "@/hooks/useDataChannel";

type CoachingStatus = "idle" | "loading" | "streaming" | "done" | "error";

export default function SessionSummaryPage() {
  const [session, setSession] = useState<SessionRecord | null>(null);
  const [coachingText, setCoachingText] = useState("");
  const [coachingStatus, setCoachingStatus] = useState<CoachingStatus>("idle");
  const [showCoaching, setShowCoaching] = useState(false);
  const coachingStarted = useRef(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const sessionId =
        typeof window !== "undefined"
          ? new URLSearchParams(window.location.search).get("sessionId")
          : null;
      const next = sessionId ? await getSessionById(sessionId) : await getLatestSession();
      if (!cancelled) setSession(next);
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const startCoaching = () => {
    if (!session || coachingStarted.current) return;
    coachingStarted.current = true;
    setShowCoaching(true);

    async function fetchCoaching() {
      setCoachingStatus("loading");
      try {
        const texts = (session!.transcript_events ?? [])
          .map((e) => e.text)
          .filter(Boolean);

        const gen = streamCoaching({
          mode: session!.mode,
          difficulty: session!.difficulty,
          duration_minutes: session!.duration_minutes,
          content_score: session!.content_score,
          delivery_score: session!.delivery_score,
          composure_score: session!.composure_score,
          final_score: session!.final_score,
          transcript_texts: texts,
          vocal_emotion: session!.latest_perception?.vocal_emotion ?? "neutral",
          face_emotion: session!.latest_perception?.face_emotion ?? "neutral",
          session_id: session!.id,
        });

        setCoachingStatus("streaming");
        for await (const chunk of gen) {
          setCoachingText((prev) => prev + chunk);
        }
        setCoachingStatus("done");
      } catch (err) {
        console.error("Coaching fetch failed:", err);
        setCoachingStatus("error");
      }
    }

    void fetchCoaching();
  };

  // Auto-start coaching when session loads
  useEffect(() => {
    if (session && !coachingStarted.current) {
      startCoaching();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session]);

  const roleName = useMemo(() => {
    if (!session) return "-";
    return jobRoles.find((r) => r.id === session.mode)?.title ?? session.mode;
  }, [session]);

  const transcriptCount = session?.transcript_events?.length ?? 0;
  const totalWords = useMemo(() => {
    if (!session?.transcript_events) return 0;
    return session.transcript_events.reduce((sum, t) => sum + (t.text?.split(" ").length ?? 0), 0);
  }, [session]);

  const avgWpm = useMemo(() => {
    if (!session?.transcript_events?.length) return 0;
    const wpms = session.transcript_events.map((t) => t.wpm).filter(Boolean);
    if (!wpms.length) return 0;
    return Math.round(wpms.reduce((a, b) => a + b, 0) / wpms.length);
  }, [session]);

  const totalFillers = useMemo(() => {
    if (!session?.transcript_events) return 0;
    return session.transcript_events.reduce((sum, t) => sum + (t.filler_count ?? 0), 0);
  }, [session]);

  const strengths = useMemo(() => {
    if (!session) return [];
    const items: string[] = [];
    if (session.content_score >= 80) items.push("Strong answer structure and relevance to prompts.");
    if (session.delivery_score >= 75) items.push("Stable speaking pace and clarity under pressure.");
    if (session.composure_score >= 75) items.push("Consistent on-camera composure and eye-line control.");
    if (avgWpm >= 130 && avgWpm <= 160) items.push("Excellent speaking pace in the ideal range.");
    if (totalFillers <= 2) items.push("Minimal filler words — clean and confident delivery.");
    return items.length > 0 ? items : ["Good completion discipline and consistent participation."];
  }, [session, avgWpm, totalFillers]);

  const opportunities = useMemo(() => {
    if (!session) return [];
    const items: string[] = [];
    if (session.content_score < 75) items.push("Add more concrete metrics and examples in each answer.");
    if (session.delivery_score < 75) items.push("Reduce filler words with shorter sentence blocks.");
    if (session.composure_score < 75) items.push("Maintain camera focus during difficult follow-ups.");
    if (avgWpm > 180) items.push("Slow down — your pace is above the ideal 130–160 WPM range.");
    if (avgWpm > 0 && avgWpm < 110) items.push("Add more detail — your pace is below the ideal 130–160 WPM range.");
    if (totalFillers > 5) items.push(`You used ${totalFillers} filler words — practice pausing instead of filling.`);
    return items.length > 0 ? items : ["Increase complexity by switching to Extensive mode next run."];
  }, [session, avgWpm, totalFillers]);

  const renderCoachingText = (text: string) => {
    return text.split("\n").map((line, i) => {
      const parts = line.split(/(\*\*[^*]+\*\*)/g);
      return (
        <p key={i} className={line.startsWith("**") ? "mt-3 first:mt-0" : "mt-1"}>
          {parts.map((part, j) =>
            part.startsWith("**") && part.endsWith("**") ? (
              <span key={j} className="font-semibold text-white">
                {part.slice(2, -2)}
              </span>
            ) : (
              <span key={j}>{part}</span>
            )
          )}
        </p>
      );
    });
  };

  return (
    <AppShell
      title="Session Summary"
      subtitle="A concise review of your latest interview run, with strengths, improvement areas, and AI coaching."
      actions={
        <div className="flex gap-2">
          <Link
            href={session ? `/reports/${session.id}` : "/reports"}
            className="rounded-full border border-white/20 bg-white/5 px-4 py-2 text-sm font-semibold transition hover:bg-white/10"
          >
            Full Report
          </Link>
          <Link
            href="/setup"
            className="rounded-full bg-qace-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400"
          >
            New Interview
          </Link>
        </div>
      }
    >
      {/* Scores Overview */}
      <section className="grid gap-4 lg:grid-cols-3">
        <GlassCard className="animate-fade-up lg:col-span-1">
          <p className="text-sm text-qace-muted">Overall Score</p>
          <p className="mt-2 text-5xl font-semibold text-qace-accent">
            {session ? session.final_score.toFixed(0) : "-"}
          </p>
          <p className="mt-2 text-sm text-qace-muted">
            Role: <span className="capitalize text-white">{roleName}</span>
          </p>
          <p className="text-sm text-qace-muted">
            Duration: <span className="text-white">{session?.duration_minutes ?? "-"}m</span>
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

      {/* Session Stats */}
      <section className="mt-4">
        <GlassCard className="animate-fade-up-delayed">
          <h3 className="mb-3 text-lg font-semibold">Session Statistics</h3>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard label="Responses" value={String(transcriptCount)} />
            <StatCard label="Total Words" value={String(totalWords)} />
            <StatCard label="Avg WPM" value={avgWpm > 0 ? String(avgWpm) : "-"} />
            <StatCard label="Filler Words" value={String(totalFillers)} />
          </div>
          {session?.latest_perception && (
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="rounded-full bg-blue-500/15 px-3 py-1 text-xs text-blue-200">
                Voice: <span className="capitalize font-medium">{session.latest_perception.vocal_emotion}</span>
              </span>
              <span className="rounded-full bg-purple-500/15 px-3 py-1 text-xs text-purple-200">
                Face: <span className="capitalize font-medium">{session.latest_perception.face_emotion}</span>
              </span>
              <span className="rounded-full bg-emerald-500/15 px-3 py-1 text-xs text-emerald-200">
                Text Quality: <span className="capitalize font-medium">{session.latest_perception.text_quality_label}</span>
              </span>
            </div>
          )}
        </GlassCard>
      </section>

      {/* Strengths / Opportunities */}
      <section className="mt-4 grid gap-4 md:grid-cols-2">
        <GlassCard className="animate-fade-up-delayed">
          <h3 className="text-lg font-semibold">Strengths</h3>
          <ul className="mt-3 space-y-2 text-sm text-qace-muted">
            {strengths.map((item) => (
              <li key={item} className="flex gap-2">
                <span className="text-emerald-400">+</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </GlassCard>

        <GlassCard className="animate-fade-up-delayed-2">
          <h3 className="text-lg font-semibold">Areas to Improve</h3>
          <ul className="mt-3 space-y-2 text-sm text-qace-muted">
            {opportunities.map((item) => (
              <li key={item} className="flex gap-2">
                <span className="text-amber-400">!</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </GlassCard>
      </section>

      {/* Transcript Timeline */}
      {session?.transcript_events && session.transcript_events.length > 0 && (
        <section className="mt-4">
          <GlassCard className="animate-fade-up-delayed-2">
            <h3 className="mb-3 text-lg font-semibold">Response Timeline</h3>
            <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
              {session.transcript_events.map((t, i) => (
                <div key={i} className="rounded-xl border border-white/10 bg-black/20 px-3 py-2.5">
                  <div className="flex items-center justify-between text-xs text-qace-muted">
                    <span>Response {i + 1}</span>
                    <div className="flex gap-3">
                      <span>{t.wpm} WPM</span>
                      <span>{t.filler_count} fillers</span>
                    </div>
                  </div>
                  <p className="mt-1 text-sm">{t.text}</p>
                </div>
              ))}
            </div>
          </GlassCard>
        </section>
      )}

      {/* Per-Question Score Breakdown */}
      {session?.per_question_scores && session.per_question_scores.length > 0 && (
        <section className="mt-4">
          <GlassCard className="animate-fade-up-delayed-2">
            <h3 className="mb-1 text-lg font-semibold">Question-by-Question Scores</h3>
            <p className="mb-3 text-xs text-qace-muted">
              Total score is the average across all questions answered.
            </p>
            <div className="space-y-3">
              {session.per_question_scores.map((q: PerQuestionScore, i: number) => (
                <div key={i} className="rounded-xl border border-white/10 bg-black/20 px-4 py-3">
                  <div className="flex items-start justify-between gap-4">
                    <p className="text-sm text-white line-clamp-2 flex-1">
                      <span className="mr-2 text-xs text-qace-muted">Q{q.index + 1}</span>
                      {q.question}
                    </p>
                    <span className="shrink-0 text-xl font-semibold text-qace-accent">{q.score.toFixed(0)}</span>
                  </div>
                  <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-qace-muted">
                    <span>Content <span className="text-white font-medium">{q.content.toFixed(0)}</span></span>
                    <span>Delivery <span className="text-white font-medium">{q.delivery.toFixed(0)}</span></span>
                    <span>Composure <span className="text-white font-medium">{q.composure.toFixed(0)}</span></span>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </section>
      )}

      {/* Scoring Explanation */}
      <section className="mt-4">
        <GlassCard className="animate-fade-up-delayed-2">
          <h3 className="mb-3 text-lg font-semibold">How Your Score is Calculated</h3>
          <div className="space-y-3 text-sm">
            <div className="rounded-xl border border-white/10 bg-black/20 px-4 py-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-white">Content Quality</span>
                <span className="text-qace-accent font-semibold">70%</span>
              </div>
              <p className="mt-1 text-qace-muted text-xs">
                Measures how well your answer addresses the question. Based on LLM text quality analysis — relevance, structure, and depth.
              </p>
            </div>
            <div className="rounded-xl border border-white/10 bg-black/20 px-4 py-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-white">Delivery</span>
                <span className="text-qace-accent font-semibold">20%</span>
              </div>
              <p className="mt-1 text-qace-muted text-xs">
                Measures speaking pace and clarity. Ideal pace is 130–160 WPM. Penalty for filler words (um, uh, like). Also factors in vocal acoustic confidence.
              </p>
            </div>
            <div className="rounded-xl border border-white/10 bg-black/20 px-4 py-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-white">Composure</span>
                <span className="text-qace-accent font-semibold">10%</span>
              </div>
              <p className="mt-1 text-qace-muted text-xs">
                Measures on-camera confidence. Combines eye contact (60%), natural blink rate near 17.5/min (25%), and positive emotional expression (15%).
              </p>
            </div>
            <p className="text-xs text-qace-muted pt-1">
              Final score = 0.70 × Content + 0.20 × Delivery + 0.10 × Composure, averaged across all answered questions.
            </p>
          </div>
        </GlassCard>
      </section>

      {/* AI Coaching */}
      <section className="mt-4">
        <GlassCard className="animate-fade-up-delayed-2">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">AI Coach</h3>
            <div className="flex items-center gap-3">
              {coachingStatus === "loading" || coachingStatus === "streaming" ? (
                <span className="flex items-center gap-2 text-xs text-qace-muted">
                  <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-qace-accent" />
                  {coachingStatus === "loading" ? "Preparing coach..." : "Coaching..."}
                </span>
              ) : coachingStatus === "done" ? (
                <span className="text-xs text-qace-muted">Done</span>
              ) : coachingStatus === "error" ? (
                <span className="text-xs text-red-400">Unavailable</span>
              ) : null}
              {!showCoaching && coachingStatus === "idle" && (
                <button
                  onClick={startCoaching}
                  className="rounded-full bg-qace-primary px-4 py-1.5 text-xs font-semibold text-white transition hover:bg-indigo-400"
                >
                  Start Coaching
                </button>
              )}
            </div>
          </div>

          <div className="mt-3 text-sm leading-relaxed text-qace-muted">
            {coachingStatus === "idle" && !showCoaching && (
              <p className="text-qace-muted opacity-50">
                The AI Coach will analyze your session and provide personalized feedback, drill plans, and improvement suggestions.
              </p>
            )}
            {coachingStatus === "loading" && (
              <p className="animate-pulse text-qace-muted">Generating your personalised coaching report...</p>
            )}
            {(coachingStatus === "streaming" || coachingStatus === "done") && coachingText && (
              <div>{renderCoachingText(coachingText)}</div>
            )}
            {coachingStatus === "error" && (
              <p className="text-red-400/80">
                Could not generate coaching. Make sure the backend is running and an LLM provider is configured.
              </p>
            )}
          </div>
        </GlassCard>
      </section>

      {/* Next Steps */}
      <section className="mt-4">
        <GlassCard className="animate-fade-up-delayed-2">
          <h3 className="mb-3 text-lg font-semibold">Next Steps</h3>
          <div className="grid gap-3 sm:grid-cols-3">
            <Link
              href="/setup"
              className="rounded-xl border border-white/10 bg-black/20 p-4 text-center transition hover:border-qace-accent/40 hover:bg-qace-accent/10"
            >
              <p className="text-2xl">🎯</p>
              <p className="mt-2 text-sm font-semibold">Retry Interview</p>
              <p className="mt-1 text-xs text-qace-muted">Try again with the same or different settings</p>
            </Link>
            <Link
              href="/practice"
              className="rounded-xl border border-white/10 bg-black/20 p-4 text-center transition hover:border-emerald-400/40 hover:bg-emerald-400/10"
            >
              <p className="text-2xl">📝</p>
              <p className="mt-2 text-sm font-semibold">Practice MCQs</p>
              <p className="mt-1 text-xs text-qace-muted">Sharpen your knowledge with targeted quizzes</p>
            </Link>
            <Link
              href="/history"
              className="rounded-xl border border-white/10 bg-black/20 p-4 text-center transition hover:border-blue-400/40 hover:bg-blue-400/10"
            >
              <p className="text-2xl">📊</p>
              <p className="mt-2 text-sm font-semibold">View History</p>
              <p className="mt-1 text-xs text-qace-muted">Track your progress across sessions</p>
            </Link>
          </div>
        </GlassCard>
      </section>
    </AppShell>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/20 p-3 text-center">
      <p className="text-2xl font-semibold text-white">{value}</p>
      <p className="mt-1 text-xs text-qace-muted">{label}</p>
    </div>
  );
}
