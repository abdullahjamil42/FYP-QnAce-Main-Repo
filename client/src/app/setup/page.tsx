"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import { Badge, GlassCard } from "@/components/ui";
import { jobRoles, interviewTypes, roundTypes } from "@/lib/mock-data";
import { loadSetupConfig, saveSetupConfig } from "@/lib/interview-session-store";
import { apiGet } from "@/lib/coding-api";

const difficulties = [
  { id: "Easy", title: "Easy", description: "Fundamentals — arrays, strings, hash maps.", icon: "🟢" },
  { id: "Medium", title: "Medium", description: "Intermediate — trees, graphs, dynamic programming.", icon: "🟡" },
  { id: "Hard", title: "Hard", description: "Advanced — complex algorithms and optimizations.", icon: "🔴" },
];

export default function SetupPage() {
  const router = useRouter();
  const [jobRole, setJobRole] = useState("software_engineer");
  const [roundType, setRoundType] = useState<"verbal" | "coding">("verbal");
  const [interviewType, setInterviewType] = useState<"quick" | "extensive">("quick");
  const [codingDifficulty, setCodingDifficulty] = useState("Easy");
  const [startingCoding, setStartingCoding] = useState(false);

  useEffect(() => {
    const existing = loadSetupConfig();
    setJobRole(existing.jobRole);
    setRoundType(existing.roundType);
    setInterviewType(existing.interviewType);
  }, []);

  useEffect(() => {
    const selected = interviewTypes.find((t) => t.id === interviewType);
    saveSetupConfig({
      mode: "technical",
      difficulty: interviewType === "extensive" ? "hard" : "standard",
      durationMinutes: selected?.durationMinutes ?? 10,
      jobRole,
      interviewType,
      roundType,
    });
  }, [jobRole, interviewType, roundType]);

  const selectedType = interviewTypes.find((t) => t.id === interviewType);

  async function handleStartCoding() {
    setStartingCoding(true);
    try {
      const res = await apiGet<{ problems: { id: number; title: string }[] }>(
        `/coding/dsa/problems?difficulty=${encodeURIComponent(codingDifficulty)}`
      );
      if (!res.problems?.length) {
        alert("No problems found for this difficulty.");
        return;
      }
      const random = res.problems[Math.floor(Math.random() * res.problems.length)];
      router.push(`/interview/coding?problemId=${random.id}&source=dsa`);
    } catch {
      alert("Failed to load problems. Is the backend running?");
    } finally {
      setStartingCoding(false);
    }
  }

  return (
    <AppShell
      title="Interview Setup"
      subtitle="Choose your target role and interview format."
      actions={
        roundType === "verbal" ? (
          <Link
            href="/session/lobby"
            className="rounded-full bg-qace-primary px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400"
          >
            Continue to Lobby
          </Link>
        ) : (
          <button
            onClick={handleStartCoding}
            disabled={startingCoding}
            className="rounded-full bg-amber-500 px-5 py-2.5 text-sm font-semibold text-black transition hover:bg-amber-400 disabled:opacity-50"
          >
            {startingCoding ? "Loading..." : "Start Coding"}
          </button>
        )
      }
    >
      {/* Job Role */}
      <section>
        <h2 className="mb-3 text-lg font-semibold">Select Job Role</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {jobRoles.map((role, index) => (
            <GlassCard
              key={role.id}
              className={
                index < 2
                  ? "animate-fade-up"
                  : index < 4
                    ? "animate-fade-up-delayed"
                    : "animate-fade-up-delayed-2"
              }
            >
              <div className="flex items-center justify-between">
                <span className="text-2xl">{role.icon}</span>
                {jobRole === role.id && <Badge tone="success">Selected</Badge>}
              </div>
              <h3 className="mt-2 text-base font-semibold">{role.title}</h3>
              <p className="mt-1 text-xs text-qace-muted">{role.description}</p>
              <button
                onClick={() => setJobRole(role.id)}
                className={`mt-3 w-full rounded-lg border px-3 py-2 text-sm font-medium transition ${
                  jobRole === role.id
                    ? "border-qace-accent bg-qace-accent/20 text-white"
                    : "border-white/20 bg-white/5 hover:bg-white/10"
                }`}
              >
                {jobRole === role.id ? "Selected" : "Select"}
              </button>
            </GlassCard>
          ))}
        </div>
      </section>

      {/* Interview Round */}
      <section className="mt-6">
        <h2 className="mb-3 text-lg font-semibold">Interview Round</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {roundTypes.map((rt) => (
            <GlassCard key={rt.id} className="animate-fade-up-delayed">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{rt.icon}</span>
                  <h3 className="text-lg font-semibold">{rt.title}</h3>
                </div>
                {roundType === rt.id && <Badge tone="success">Selected</Badge>}
              </div>
              <p className="mt-2 text-sm text-qace-muted">{rt.description}</p>
              <button
                onClick={() => setRoundType(rt.id as "verbal" | "coding")}
                className={`mt-4 w-full rounded-lg border px-3 py-2 text-sm font-medium transition ${
                  roundType === rt.id
                    ? "border-qace-accent bg-qace-accent/20 text-white"
                    : "border-white/20 bg-white/5 hover:bg-white/10"
                }`}
              >
                {roundType === rt.id ? "Selected" : "Select"}
              </button>
            </GlassCard>
          ))}
        </div>
      </section>

      {/* Verbal → Interview Format */}
      {roundType === "verbal" && (
        <section className="mt-6">
          <h2 className="mb-3 text-lg font-semibold">Interview Format</h2>
          <div className="grid gap-4 md:grid-cols-2">
            {interviewTypes.map((type) => (
              <GlassCard key={type.id} className="animate-fade-up-delayed">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold">{type.title}</h3>
                  {interviewType === type.id && <Badge tone="success">Selected</Badge>}
                </div>
                <p className="mt-2 text-sm text-qace-muted">{type.description}</p>
                <div className="mt-3 flex items-center gap-3 text-xs text-qace-muted">
                  <span>{type.durationMinutes > 0 ? `${type.durationMinutes} min` : "No limit"}</span>
                  <span>~{type.questionCount} questions</span>
                  {type.id === "extensive" && <Badge tone="warning">Emotion Analysis</Badge>}
                </div>
                <button
                  onClick={() => setInterviewType(type.id as "quick" | "extensive")}
                  className={`mt-4 w-full rounded-lg border px-3 py-2 text-sm font-medium transition ${
                    interviewType === type.id
                      ? "border-qace-accent bg-qace-accent/20 text-white"
                      : "border-white/20 bg-white/5 hover:bg-white/10"
                  }`}
                >
                  {interviewType === type.id ? "Selected" : "Select"}
                </button>
              </GlassCard>
            ))}
          </div>
        </section>
      )}

      {/* Coding → Difficulty Selection */}
      {roundType === "coding" && (
        <section className="mt-6">
          <h2 className="mb-3 text-lg font-semibold">Problem Difficulty</h2>
          <div className="grid gap-4 md:grid-cols-3">
            {difficulties.map((d) => (
              <GlassCard key={d.id} className="animate-fade-up-delayed">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">{d.icon}</span>
                    <h3 className="text-lg font-semibold">{d.title}</h3>
                  </div>
                  {codingDifficulty === d.id && <Badge tone="success">Selected</Badge>}
                </div>
                <p className="mt-2 text-sm text-qace-muted">{d.description}</p>
                <button
                  onClick={() => setCodingDifficulty(d.id)}
                  className={`mt-4 w-full rounded-lg border px-3 py-2 text-sm font-medium transition ${
                    codingDifficulty === d.id
                      ? "border-qace-accent bg-qace-accent/20 text-white"
                      : "border-white/20 bg-white/5 hover:bg-white/10"
                  }`}
                >
                  {codingDifficulty === d.id ? "Selected" : "Select"}
                </button>
              </GlassCard>
            ))}
          </div>
        </section>
      )}

      {/* Session Preview */}
      <section className="mt-6">
        <GlassCard className="animate-fade-up-delayed-2">
          <h3 className="text-base font-semibold">Session Preview</h3>
          <div className="mt-3 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
            <div>
              <p className="text-xs text-qace-muted">Role</p>
              <p className="mt-0.5 font-medium capitalize">{jobRoles.find((r) => r.id === jobRole)?.title}</p>
            </div>
            <div>
              <p className="text-xs text-qace-muted">Round</p>
              <p className="mt-0.5 font-medium">{roundTypes.find((r) => r.id === roundType)?.title}</p>
            </div>
            {roundType === "verbal" ? (
              <>
                <div>
                  <p className="text-xs text-qace-muted">Format</p>
                  <p className="mt-0.5 font-medium">{selectedType?.title}</p>
                </div>
                <div>
                  <p className="text-xs text-qace-muted">Duration</p>
                  <p className="mt-0.5 font-medium">{selectedType && selectedType.durationMinutes > 0 ? `${selectedType.durationMinutes} min` : "Unlimited"}</p>
                </div>
              </>
            ) : (
              <>
                <div>
                  <p className="text-xs text-qace-muted">Difficulty</p>
                  <p className="mt-0.5 font-medium">{codingDifficulty}</p>
                </div>
                <div>
                  <p className="text-xs text-qace-muted">Language</p>
                  <p className="mt-0.5 font-medium">Python 3</p>
                </div>
              </>
            )}
          </div>
        </GlassCard>
      </section>
    </AppShell>
  );
}
