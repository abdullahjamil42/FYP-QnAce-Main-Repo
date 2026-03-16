"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import InteractiveNetworkBg from "@/components/InteractiveNetworkBg";
import BrandLogo from "@/components/BrandLogo";

const benefitCards = [
  {
    title: "AI Interview Presence",
    text: "A speaking interviewer avatar, contextual follow-ups, and realistic pressure cues that feel like an actual call.",
  },
  {
    title: "Multimodal Intelligence",
    text: "Transcript quality, pacing, vocal emotion, and composure signals combined into one score stream.",
  },
  {
    title: "Session Memory",
    text: "Track every interview, compare trends, and know exactly which communication habits to improve next.",
  },
];

const journey = [
  {
    step: "Step 1",
    title: "Pick your interview mode",
    detail: "Configure technical, behavioral, or leadership tracks with custom difficulty and timing.",
  },
  {
    step: "Step 2",
    title: "Run a live AI call",
    detail: "Join a meeting-style room with an AI interviewer, transcript timeline, and response scoring.",
  },
  {
    step: "Step 3",
    title: "Review and improve",
    detail: "Use report breakdowns and trend analytics to practice weak points with focus drills.",
  },
];

export default function LandingPage() {
  const [scrollShadeOpacity, setScrollShadeOpacity] = useState(0);

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

  useEffect(() => {
    let rafId = 0;

    const handleScroll = () => {
      if (rafId) {
        window.cancelAnimationFrame(rafId);
      }
      rafId = window.requestAnimationFrame(() => {
        const maxScroll = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
        const progress = Math.min(1, Math.max(0, window.scrollY / maxScroll));
        setScrollShadeOpacity(progress * 0.24);
      });
    };

    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });

    return () => {
      if (rafId) {
        window.cancelAnimationFrame(rafId);
      }
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  return (
    <main className="liquid-page relative min-h-screen overflow-x-hidden text-qace-text">
      <InteractiveNetworkBg />
      <div className="liquid-bg" />
      <div className="liquid-noise" />
      <div className="landing-scroll-shade" style={{ opacity: scrollShadeOpacity }} />

      <header className="relative z-10 mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-6 md:px-8">
        <Link href="/" className="flex items-center gap-2">
          <BrandLogo className="h-9 w-auto text-white" />
          <span className="text-xl font-semibold tracking-tight text-white">
            Q&A<span className="text-sky-400">ce</span>
          </span>
        </Link>
        <div className="flex items-center gap-2">
          <Link
            href="/login"
            className="rounded-full border border-white/25 bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/15"
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

      <section className="relative z-10 mx-auto flex min-h-[calc(100vh-80px)] w-full max-w-6xl items-center px-5 pb-8 pt-6 md:px-8 md:pt-10">
        <div data-reveal className="reveal space-y-6 text-center">
          <p className="inline-flex rounded-full border border-cyan-300/35 px-3 py-1 text-xs font-semibold tracking-wide text-cyan-100">
            AI powered interview coach 
          </p>
          <h1 className="text-4xl font-semibold leading-tight md:text-6xl">
            <span className="bg-gradient-to-r from-indigo-300 via-sky-400 to-purple-600 bg-clip-text text-transparent">Master your Interviews</span>{" "}
            <span className="text-white">with AI-Powered Mocks and Feedback</span>
          </h1>
          <p className="mx-auto max-w-xl text-base text-qace-muted md:text-lg">
            Get multimodal feedback on your interview performance, track your progress over time, and practice with an AI interviewer that feels real.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              href="/setup"
              className="rounded-full bg-qace-primary px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-cyan-500/20 transition hover:-translate-y-0.5 hover:bg-indigo-400"
            >
              Continue to App
            </Link>
            <Link
              href="/session/live"
              className="rounded-full border border-white/25 bg-white/10 px-6 py-3 text-sm font-semibold text-white transition hover:bg-white/15"
            >
              Open Live Interview
            </Link>
          </div>
        </div>

       {/*<div data-reveal className="reveal reveal-delay-1">
          <div className="card-glow panel-tilt relative overflow-hidden rounded-3xl border border-white/20 bg-white/5 p-6 backdrop-blur-md">
            <div className="mb-5 flex items-center justify-between text-white">
              <p className="text-sm text-qace-muted">Meeting Snapshot</p>
              <span className="rounded-full bg-emerald-500/25 px-2 py-1 text-xs text-emerald-200">AI live</span>
            </div>
            <div className="space-y-4">
              <InfoRow label="Conte nt Quality" value="86 / 100" />
              <InfoRow label="Delivery" value="79 / 100" />
              <InfoRow label="Composure" value="81 / 100" />
            </div>
            <div className="mt-6 rounded-2xl border border-white/15 bg-black/20 p-4">
              <p className="text-xs uppercase tracking-wide text-qace-muted">Coach Note</p>
              <p className="mt-2 text-sm text-white">
                Great pacing and confidence. Next upgrade: sharper impact metrics and tighter closing statements.
              </p>
            </div>
          </div>
        </div>*/}
      </section>

      <section className="relative z-10 mx-auto w-full max-w-6xl space-y-5 px-5 pb-14 md:px-8">
        <div data-reveal className="reveal">
          <h2 className="text-2xl font-semibold text-white md:text-3xl">Built for realistic prep loops</h2>
          <p className="mt-2 max-w-2xl text-qace-muted">
            The fastest way to improve is a realistic mock + measurable feedback + immediate retry. This page is designed around that cycle.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {benefitCards.map((card, index) => (
            <article
              key={card.title}
              data-reveal
              className={`reveal card-glow rounded-2xl border border-white/20 bg-white/5 p-5 shadow-xl shadow-black/20 ${
                index === 1 ? "reveal-delay-1" : index === 2 ? "reveal-delay-2" : ""
              }`}
            >
              <h3 className="text-lg font-semibold text-white">{card.title}</h3>
              <p className="mt-2 text-sm text-qace-muted">{card.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="relative z-10 mx-auto w-full max-w-6xl px-5 pb-20 md:px-8">
        <div data-reveal className="reveal mb-6">
          <h2 className="text-2xl font-semibold text-white md:text-3xl">Your interview journey</h2>
          <p className="mt-2 text-qace-muted">Scroll through the full workflow before you enter the session room.</p>
        </div>
        <div className="space-y-4">
          {journey.map((item, index) => (
            <article
              key={item.title}
              data-reveal
              className={`reveal card-glow rounded-2xl border border-white/20 bg-white/5 p-6 ${
                index === 1 ? "reveal-delay-1" : index === 2 ? "reveal-delay-2" : ""
              }`}
            >
              <p className="text-xs uppercase tracking-wide text-qace-muted">{item.step}</p>
              <h3 className="mt-2 text-2xl font-semibold text-white">{item.title}</h3>
              <p className="mt-2 max-w-2xl text-sm text-qace-muted">{item.detail}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="relative z-10 mx-auto w-full max-w-6xl px-5 pb-28 md:px-8">
        <div data-reveal className="reveal card-glow rounded-3xl border border-white/25 bg-white/5 p-8 text-center">
          <p className="text-xs uppercase tracking-[0.2em] text-qace-muted">Ready for your next interview?</p>
          <h2 className="mt-3 text-3xl font-semibold text-white md:text-4xl">Launch your AI mock interview now.</h2>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <Link href="/setup" className="rounded-full bg-qace-primary px-6 py-3 text-sm font-semibold text-white transition hover:bg-indigo-400">
              Continue
            </Link>
            <Link href="/login" className="rounded-full border border-white/25 bg-white/10 px-6 py-3 text-sm font-semibold text-white transition hover:bg-white/15">
              Login
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="card-glow rounded-xl border border-white/15 bg-black/20 p-3">
      <p className="text-xs uppercase tracking-wide text-qace-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold text-white">{value}</p>
    </div>
  );
}
