"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import BrandLogo from "@/components/BrandLogo";

type AuthSplitLayoutProps = {
  mode: "login" | "signup";
  title: string;
  subtitle: string;
  children: ReactNode;
};

export default function AuthSplitLayout({ mode, title, subtitle, children }: AuthSplitLayoutProps) {
  return (
    <main className="liquid-page relative min-h-screen overflow-hidden text-qace-text">
      <div className="liquid-bg" />
      <div className="liquid-noise" />

      <header className="relative z-10 mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-6 md:px-8">
        <Link href="/" className="flex items-center gap-2">
          <BrandLogo className="h-9 w-auto text-white" />
          <span className="text-xl font-semibold tracking-tight text-white">
            Q&A<span className="text-sky-400">ce</span>
          </span>
        </Link>
      </header>

      <section className="relative z-10 mx-auto grid w-full max-w-6xl gap-8 px-5 pb-10 md:px-8 lg:min-h-[calc(100vh-88px)] lg:grid-cols-2 lg:items-center">
        <div className="auth-left-shift space-y-6 lg:pr-8">
          <p className="inline-flex rounded-full border border-cyan-300/35 px-3 py-1 text-xs font-semibold tracking-wide text-cyan-100">
            AI powered interview coach
          </p>
          <h1 className="text-4xl font-semibold leading-tight md:text-5xl">
            <span className="bg-gradient-to-r from-indigo-300 via-sky-400 to-purple-600 bg-clip-text text-transparent">Master your Interviews</span>{" "}
            <span className="text-white">with AI-Powered Mocks and Feedback</span>
          </h1>
          <p className="max-w-xl text-base text-qace-muted md:text-lg">
            Get multimodal feedback on your interview performance, track your progress over time, and practice with an AI interviewer that feels real.
          </p>
        </div>

        <div className="auth-right-appear">
          <div className="card-glow rounded-3xl border border-white/20 bg-white/10 p-6 backdrop-blur-md md:p-7">
            <div className="mb-5 grid grid-cols-2 gap-2 rounded-xl border border-white/15 bg-black/20 p-1">
              <Link
                href="/login"
                className={`rounded-lg px-3 py-2 text-center text-sm font-semibold transition ${
                  mode === "login" ? "bg-qace-primary text-white" : "text-qace-muted hover:bg-white/10 hover:text-white"
                }`}
              >
                Login
              </Link>
              <Link
                href="/signup"
                className={`rounded-lg px-3 py-2 text-center text-sm font-semibold transition ${
                  mode === "signup" ? "bg-qace-primary text-white" : "text-qace-muted hover:bg-white/10 hover:text-white"
                }`}
              >
                Signup
              </Link>
            </div>

            <div className="mb-4">
              <h2 className="text-2xl font-semibold text-white">{title}</h2>
              <p className="mt-1 text-sm text-qace-muted">{subtitle}</p>
            </div>

            {children}
          </div>
        </div>
      </section>
    </main>
  );
}
