"use client";

import Link from "next/link";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 p-8">
      {/* Logo / Title */}
      <div className="text-center">
        <h1 className="text-5xl font-bold tracking-tight">
          Q&<span className="text-qace-primary">Ace</span>
        </h1>
        <p className="mt-3 text-lg text-qace-muted">
          Real-time AI interview preparation
        </p>
      </div>

      {/* Quick Start */}
      <div className="flex flex-col items-center gap-4 rounded-2xl bg-qace-surface p-8 shadow-xl">
        <p className="max-w-md text-center text-qace-muted">
          Practice your interview skills with an AI interviewer that analyzes
          your speech, facial expressions, and composure in real time.
        </p>

        <Link
          href="/session"
          className="mt-4 rounded-xl bg-qace-primary px-8 py-3 text-lg font-semibold text-white
                     transition-all hover:bg-indigo-500 hover:shadow-lg active:scale-95"
        >
          Start Interview →
        </Link>
      </div>

      {/* Features Grid */}
      <div className="mt-4 grid max-w-2xl grid-cols-3 gap-6 text-center text-sm text-qace-muted">
        <div>
          <div className="mb-1 text-2xl">🎤</div>
          <div>Speech Analysis</div>
          <div className="text-xs">WPM, fillers, clarity</div>
        </div>
        <div>
          <div className="mb-1 text-2xl">😊</div>
          <div>Facial Analysis</div>
          <div className="text-xs">Emotion &amp; eye contact</div>
        </div>
        <div>
          <div className="mb-1 text-2xl">⚡</div>
          <div>&lt;800ms Response</div>
          <div className="text-xs">Ultra-low latency AI</div>
        </div>
      </div>
    </main>
  );
}
