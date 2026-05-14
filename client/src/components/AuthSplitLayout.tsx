"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import BrandLogo from "@/components/BrandLogo";
import BackButton from "@/components/BackButton";
import Footer from "@/components/Footer";

type AuthSplitLayoutProps = {
  mode: "login" | "signup";
  title: string;
  subtitle: string;
  children: ReactNode;
};

export default function AuthSplitLayout({ mode, title, subtitle, children }: AuthSplitLayoutProps) {
  return (
    <main className="liquid-page relative flex min-h-screen flex-col overflow-hidden text-qace-text">
      <div className="liquid-bg" />
      <div className="liquid-noise" />

      <header className="relative z-10 mx-auto flex w-full max-w-6xl items-center justify-between gap-3 px-4 py-4 sm:px-6 sm:py-6 md:px-8">
        <Link href="/" className="flex items-center gap-2">
          <BrandLogo className="h-8 w-auto text-white sm:h-9" />
          <span className="text-lg font-semibold tracking-tight text-white sm:text-xl">
            Q&A<span className="text-sky-400">ce</span>
          </span>
        </Link>
        <BackButton fallbackHref="/" />
      </header>

      <section className="relative z-10 mx-auto grid w-full max-w-6xl flex-1 gap-8 px-4 pb-10 sm:px-6 md:px-8 lg:grid-cols-2 lg:items-center">
        <div className="auth-left-shift space-y-5 text-center sm:space-y-6 lg:pr-8 lg:text-left">
          <p className="inline-flex rounded-full border border-cyan-300/35 px-3 py-1 text-[11px] font-semibold tracking-wide text-cyan-100 sm:text-xs">
            AI powered interview coach
          </p>
          <h1 className="text-3xl font-semibold leading-tight sm:text-4xl md:text-5xl">
            <span className="bg-gradient-to-r from-indigo-300 via-sky-400 to-purple-600 bg-clip-text text-transparent">
              Master your Interviews
            </span>{" "}
            <span className="text-white">with AI-Powered Mocks and Feedback</span>
          </h1>
          <p className="mx-auto max-w-xl text-sm text-qace-muted sm:text-base md:text-lg lg:mx-0">
            Get multimodal feedback on your interview performance, track your progress over time, and practice with an AI interviewer that feels real.
          </p>
        </div>

        <div className="auth-right-appear">
          <div className="card-glow rounded-3xl border border-white/20 bg-white/10 p-5 backdrop-blur-md sm:p-6 md:p-7">
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
              <h2 className="text-xl font-semibold text-white sm:text-2xl">{title}</h2>
              <p className="mt-1 text-sm text-qace-muted">{subtitle}</p>
            </div>

            {children}
          </div>
        </div>
      </section>

      <Footer variant="marketing" />
    </main>
  );
}
