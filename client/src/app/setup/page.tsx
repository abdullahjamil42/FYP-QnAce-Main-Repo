"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/AppShell";
import { Badge } from "@/components/ui";
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
      {/* Single unified glass container — same design as NotesChatWidget */}
      <div className="card-glow animate-fade-up overflow-hidden rounded-2xl border border-white/20 bg-white/5 shadow-xl shadow-black/40 backdrop-blur-md">

        {/* Job Role */}
        <div className="border-b border-white/10 px-5 py-5">
          <h2 className="mb-3 text-lg font-semibold">Select Job Role</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            {jobRoles.map((role) => (
              <button
                key={role.id}
                type="button"
                onClick={() => setJobRole(role.id)}
                className={`rounded-xl border p-4 text-left transition ${
                  jobRole === role.id
                    ? "border-qace-accent bg-qace-accent/10"
                    : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-2xl">{role.icon}</span>
                  {jobRole === role.id && <Badge tone="success">Selected</Badge>}
                </div>
                <h3 className="mt-2 text-sm font-semibold">{role.title}</h3>
                <p className="mt-1 text-xs text-qace-muted">{role.description}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Interview Round */}
        <div className="border-b border-white/10 px-5 py-5">
          <h2 className="mb-3 text-lg font-semibold">Interview Round</h2>
          <div className="grid gap-4 md:grid-cols-2">
            {roundTypes.map((rt) => (
              <button
                key={rt.id}
                type="button"
                onClick={() => setRoundType(rt.id as "verbal" | "coding")}
                className={`rounded-xl border p-4 text-left transition ${
                  roundType === rt.id
                    ? "border-qace-accent bg-qace-accent/10"
                    : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">{rt.icon}</span>
                    <h3 className="text-lg font-semibold">{rt.title}</h3>
                  </div>
                  {roundType === rt.id && <Badge tone="success">Selected</Badge>}
                </div>
                <p className="mt-2 text-sm text-qace-muted">{rt.description}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Verbal → Interview Format */}
        {roundType === "verbal" && (
          <div className="border-b border-white/10 px-5 py-5">
            <h2 className="mb-3 text-lg font-semibold">Interview Format</h2>
            <div className="grid gap-4 md:grid-cols-2">
              {interviewTypes.map((type) => (
                <button
                  key={type.id}
                  type="button"
                  onClick={() => setInterviewType(type.id as "quick" | "extensive")}
                  className={`rounded-xl border p-4 text-left transition ${
                    interviewType === type.id
                      ? "border-qace-accent bg-qace-accent/10"
                      : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10"
                  }`}
                >
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
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Coding → Difficulty Selection */}
        {roundType === "coding" && (
          <div className="border-b border-white/10 px-5 py-5">
            <h2 className="mb-3 text-lg font-semibold">Problem Difficulty</h2>
            <div className="grid gap-4 md:grid-cols-3">
              {difficulties.map((d) => (
                <button
                  key={d.id}
                  type="button"
                  onClick={() => setCodingDifficulty(d.id)}
                  className={`rounded-xl border p-4 text-left transition ${
                    codingDifficulty === d.id
                      ? "border-qace-accent bg-qace-accent/10"
                      : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{d.icon}</span>
                      <h3 className="text-lg font-semibold">{d.title}</h3>
                    </div>
                    {codingDifficulty === d.id && <Badge tone="success">Selected</Badge>}
                  </div>
                  <p className="mt-2 text-sm text-qace-muted">{d.description}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Session Preview */}
        <div className="px-5 py-5">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-qace-muted">Session Preview</p>
          <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
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
        </div>

      </div>
    </AppShell>
  );
}
