"use client";

import Link from "next/link";
import { useEffect } from "react";

const benefitCards = [
  {
    title: "Live AI Interviewer",
    text: "Practice with a real-time interviewer that adapts follow-up questions to your responses.",
  },
  {
    title: "Multimodal Feedback",
    text: "Get insights from transcript quality, vocal emotion, pacing, and camera presence.",
  },
  {
    title: "Progress Intelligence",
    text: "Track score trends across sessions and focus where your growth curve is highest.",
  },
];

export default function LandingPage() {
  useEffect(() => {
    const elements = Array.from(document.querySelectorAll<HTMLElement>("[data-reveal]"));
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
          }
        });
      },
      {
        rootMargin: "0px 0px -12% 0px",
        threshold: 0.15,
      }
    );

    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, []);

  return (
    <main className="relative min-h-screen overflow-x-hidden bg-qace-dark text-qace-text">
      <div className="landing-aurora pointer-events-none absolute inset-0" />

      <header className="relative z-10 mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-5 md:px-8">
        <p className="text-xl font-semibold tracking-tight">
          Q&<span className="text-qace-accent">Ace</span>
        </p>
        <div className="flex items-center gap-2">
          <Link
            href="/login"
            className="rounded-full border border-white/20 bg-white/5 px-4 py-2 text-sm font-semibold transition hover:bg-white/10"
          >
            Login
          </Link>
          <Link
            href="/signup"
            className="rounded-full bg-qace-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400"
          >
            Signup
          </Link>
        </div>
      </header>

      <section className="relative z-10 mx-auto grid w-full max-w-6xl gap-8 px-5 pb-16 pt-8 md:grid-cols-2 md:px-8 md:pt-16">
        <div data-reveal className="reveal space-y-5">
          <p className="inline-flex rounded-full border border-cyan-300/30 bg-cyan-300/10 px-3 py-1 text-xs font-semibold tracking-wide text-cyan-100">
            Interview preparation, reimagined
          </p>
          <h1 className="text-4xl leading-tight md:text-6xl">
            Build interview confidence with feedback you can act on.
          </h1>
          <p className="max-w-xl text-base text-qace-muted md:text-lg">
            Q&Ace helps you train technical and behavioral interviews using an AI interviewer, real-time perception analysis, and clean score breakdowns that show what to improve next.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/setup"
              className="rounded-full bg-gradient-to-r from-qace-primary to-cyan-400 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-cyan-500/20 transition hover:-translate-y-0.5"
            >
              Continue to App
            </Link>
            <Link
              href="/session/live"
              className="rounded-full border border-white/25 bg-black/20 px-6 py-3 text-sm font-semibold transition hover:bg-black/35"
            >
              Try Live Demo
            </Link>
          </div>
        </div>

        <div data-reveal className="reveal reveal-delay-1">
          <div className="panel-tilt relative overflow-hidden rounded-3xl border border-white/15 bg-gradient-to-b from-white/10 to-black/25 p-6 backdrop-blur-md">
            <div className="mb-5 flex items-center justify-between">
              <p className="text-sm text-qace-muted">Session Snapshot</p>
              <span className="rounded-full bg-emerald-400/20 px-2 py-1 text-xs text-emerald-200">Live</span>
            </div>
            <div className="space-y-4">
              <InfoRow label="Content Quality" value="86 / 100" />
              <InfoRow label="Delivery" value="79 / 100" />
              <InfoRow label="Composure" value="81 / 100" />
            </div>
            <div className="mt-6 rounded-2xl border border-white/10 bg-black/20 p-4">
              <p className="text-xs uppercase tracking-wide text-qace-muted">AI Coach Note</p>
              <p className="mt-2 text-sm text-slate-100">
                Strong structure and confidence. Next step: reduce filler words in long responses and quantify impact metrics.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="relative z-10 mx-auto w-full max-w-6xl space-y-5 px-5 pb-12 md:px-8">
        <div data-reveal className="reveal">
          <h2 className="text-2xl md:text-3xl">Why Q&Ace works</h2>
          <p className="mt-2 max-w-2xl text-qace-muted">
            Practice loops are only useful when feedback is immediate, specific, and measurable. Q&Ace gives you that loop in one streamlined flow.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {benefitCards.map((card, index) => (
            <article
              key={card.title}
              data-reveal
              className={`reveal rounded-2xl border border-white/10 bg-white/5 p-5 shadow-xl shadow-black/20 ${
                index === 1 ? "reveal-delay-1" : index === 2 ? "reveal-delay-2" : ""
              }`}
            >
              <h3 className="text-lg font-semibold">{card.title}</h3>
              <p className="mt-2 text-sm text-qace-muted">{card.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="relative z-10 mx-auto grid w-full max-w-6xl gap-4 px-5 pb-24 md:grid-cols-3 md:px-8">
        <div data-reveal className="reveal sticky-card rounded-2xl border border-white/10 bg-black/25 p-5">
          <p className="text-xs uppercase tracking-wide text-qace-muted">Step 1</p>
          <h3 className="mt-2 text-xl">Configure</h3>
          <p className="mt-2 text-sm text-qace-muted">Pick interview mode, difficulty, and session length based on your target role.</p>
        </div>
        <div data-reveal className="reveal reveal-delay-1 sticky-card rounded-2xl border border-white/10 bg-black/25 p-5">
          <p className="text-xs uppercase tracking-wide text-qace-muted">Step 2</p>
          <h3 className="mt-2 text-xl">Perform</h3>
          <p className="mt-2 text-sm text-qace-muted">Run a live mock interview with dynamic prompts and multimodal analysis in real time.</p>
        </div>
        <div data-reveal className="reveal reveal-delay-2 sticky-card rounded-2xl border border-white/10 bg-black/25 p-5">
          <p className="text-xs uppercase tracking-wide text-qace-muted">Step 3</p>
          <h3 className="mt-2 text-xl">Improve</h3>
          <p className="mt-2 text-sm text-qace-muted">Review scores, coaching notes, and trend analytics, then practice the next targeted drill.</p>
        </div>
      </section>
    </main>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/20 p-3">
      <p className="text-xs uppercase tracking-wide text-qace-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  );
}
