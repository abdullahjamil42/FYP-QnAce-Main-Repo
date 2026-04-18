"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import CodingRoundView from "@/components/coding/CodingRoundView";

function CodingPageInner() {
  const router = useRouter();
  const sp = useSearchParams();
  const problemId = sp.get("problemId") || "";
  const sessionId = sp.get("sessionId") || "";

  if (!problemId) {
    return (
      <main className="mx-auto max-w-lg p-8 text-center text-qace-muted">
        <p>Add a problem id to the URL, for example:</p>
        <code className="mt-4 block rounded-lg bg-black/40 p-3 text-sm text-white/90">
          /interview/coding?problemId=&lt;uuid&gt;&amp;sessionId=&lt;optional-webrtc-id&gt;
        </code>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-[1400px]">
      <header className="flex items-center gap-3 px-4 pt-4 md:px-6 md:pt-6">
        <button
          onClick={() => {
            if (!confirm("Leave the coding round and go back?")) return;
            router.push("/setup");
          }}
          className="rounded-lg border border-white/10 bg-white/5 p-1.5 text-qace-muted transition hover:bg-white/10 hover:text-white"
          title="Back to Setup"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <h1 className="text-lg font-semibold text-white/90">Coding Round</h1>
      </header>
      <CodingRoundView problemId={problemId} sessionId={sessionId || undefined} />
    </main>
  );
}

export default function InterviewCodingPage() {
  return (
    <Suspense
      fallback={
        <main className="p-8 text-center text-qace-muted">Loading coding round…</main>
      }
    >
      <CodingPageInner />
    </Suspense>
  );
}
