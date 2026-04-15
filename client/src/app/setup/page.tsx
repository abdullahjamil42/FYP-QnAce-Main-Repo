"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { Badge, GlassCard } from "@/components/ui";
import { setupDifficulties, setupTracks } from "@/lib/mock-data";
import { loadSetupConfig, saveSetupConfig } from "@/lib/interview-session-store";

export default function SetupPage() {
  const [mode, setMode] = useState("technical");
  const [difficulty, setDifficulty] = useState("Standard");
  const [duration, setDuration] = useState(20);

  useEffect(() => {
    const existing = loadSetupConfig();
    setMode(existing.mode);
    setDifficulty(existing.difficulty);
    setDuration(existing.durationMinutes);
  }, []);

  useEffect(() => {
    const existing = loadSetupConfig();
    saveSetupConfig({
      ...existing,
      mode,
      difficulty,
      durationMinutes: duration,
    });
  }, [mode, difficulty, duration]);

  return (
    <AppShell
      title="Interview Setup"
      subtitle="Choose your interview track, difficulty, and pacing. This configuration prepares your scoring rubric and live prompts."
      actions={
        <Link
          href="/session/lobby"
          className="rounded-full bg-qace-primary px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400"
        >
          Continue to Lobby
        </Link>
      }
    >
      <section className="grid gap-4 lg:grid-cols-3">
        {setupTracks.map((track, index) => (
          <GlassCard key={track.id} className={index === 0 ? "animate-fade-up" : index === 1 ? "animate-fade-up-delayed" : "animate-fade-up-delayed-2"}>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">{track.title}</h2>
              <Badge>{mode === track.id ? "Selected" : "Track"}</Badge>
            </div>
            <p className="mt-2 text-sm text-qace-muted">{track.description}</p>
            <button
              onClick={() => setMode(track.id)}
              className={`mt-4 rounded-lg border px-3 py-2 text-sm font-medium transition ${
                mode === track.id
                  ? "border-qace-accent bg-qace-accent/20 text-white"
                  : "border-white/20 bg-white/5 hover:bg-white/10"
              }`}
            >
              Select {track.title}
            </button>
          </GlassCard>
        ))}
      </section>

      <section className="mt-4 grid gap-4 md:grid-cols-2">
        <GlassCard className="animate-fade-up-delayed">
          <h3 className="text-lg font-semibold">Difficulty</h3>
          <div className="mt-3 flex flex-wrap gap-2">
            {setupDifficulties.map((difficultyOption) => (
              <button
                key={difficultyOption}
                onClick={() => setDifficulty(difficultyOption)}
                className={`rounded-full border px-4 py-2 text-sm transition ${
                  difficulty === difficultyOption
                    ? "border-qace-accent/70 bg-qace-accent/20 text-white"
                    : "border-white/15 bg-black/20 hover:border-qace-accent/60 hover:text-white"
                }`}
              >
                {difficultyOption}
              </button>
            ))}
          </div>
        </GlassCard>

        <GlassCard className="animate-fade-up-delayed-2">
          <h3 className="text-lg font-semibold">Session Length</h3>
          <p className="mt-2 text-sm text-qace-muted">Pick a target duration to fit your prep schedule.</p>
          <div className="mt-3 grid grid-cols-3 gap-2 text-sm">
            {[
              { minutes: 10, label: "Sprint" },
              { minutes: 20, label: "Standard" },
              { minutes: 35, label: "Deep Drill" },
            ].map((slot) => (
              <button
                key={slot.minutes}
                onClick={() => setDuration(slot.minutes)}
                className={`rounded-lg border px-3 py-2 transition ${
                  duration === slot.minutes
                    ? "border-qace-accent/70 bg-qace-accent/20"
                    : "border-white/15 bg-black/20 hover:bg-white/10"
                }`}
              >
                <p className="font-semibold">{slot.minutes} min</p>
                <p className="text-xs text-qace-muted">{slot.label}</p>
              </button>
            ))}
          </div>
        </GlassCard>
      </section>
    </AppShell>
  );
}
