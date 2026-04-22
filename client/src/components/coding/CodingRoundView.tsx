"use client";

import Editor from "@monaco-editor/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { apiGet, apiPost } from "@/lib/coding-api";

export type ProblemPayload = {
  id: string;
  title: string;
  difficulty: string;
  topics: unknown;
  description: string;
  examples: unknown;
  constraints: string;
  hints: unknown;
};

const LANGS: { id: number; label: string }[] = [{ id: 71, label: "Python 3" }];

type RunResultRow = {
  stdin: string;
  stdout: string;
  stderr?: string;
  expected: string;
  passed: boolean;
  time?: unknown;
  memory?: unknown;
  status?: string;
};

type ScoringPayload = {
  correctness: { passed: number; total: number; failed_cases: unknown[] };
  complexity: {
    time: string;
    space: string;
    is_optimal: boolean;
    optimal: string;
    explanation: string;
  };
  quality: { observations: string[]; score: number };
  time_taken_seconds: number;
  empirical_ms?: { n100?: number | null; n1000?: number | null; n10000?: number | null };
};

type CodingRoundViewProps = {
  problemId: string;
  sessionId?: string;
  /** Called after submit scoring + optional tier-3 analyze; parent triggers avatar / DataChannel */
  onDebriefRequest?: (scoring: ScoringPayload) => void;
  onClose?: () => void;
};

export default function CodingRoundView({
  problemId,
  sessionId = "",
  onDebriefRequest,
  onClose,
}: CodingRoundViewProps) {
  const [problem, setProblem] = useState<ProblemPayload | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [code, setCode] = useState(
    'name = input().strip()\nprint(f"Hello, {name}")\n'
  );
  const [lang, setLang] = useState(71);
  const [consoleText, setConsoleText] = useState("");
  const [hintCard, setHintCard] = useState<string | null>(null);
  const [scoring, setScoring] = useState<ScoringPayload | null>(null);
  const [busy, setBusy] = useState(false);
  const [isDsa, setIsDsa] = useState(false);

  const [elapsed, setElapsed] = useState(0); // seconds since problem loaded

  const startedAtRef = useRef<number>(Date.now());
  const lastKeyAtRef = useRef<number>(Date.now());
  const hintLevelRef = useRef(0);
  const idleTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastRunSigRef = useRef<string>("");
  const runRepeatRef = useRef(0);

  // Tick the elapsed timer every second
  useEffect(() => {
    startedAtRef.current = Date.now();
    setElapsed(0);
    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAtRef.current) / 1000));
    }, 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [problemId]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const urlParams = typeof window !== "undefined"
          ? new URLSearchParams(window.location.search)
          : new URLSearchParams();
        const dsaMode = urlParams.get("source") === "dsa";
        if (!cancelled) setIsDsa(dsaMode);
        const endpoint = dsaMode
          ? `/coding/dsa/problems/${problemId}`
          : `/coding/problems/${problemId}`;
        const p = await apiGet<ProblemPayload>(endpoint);
        if (!cancelled) setProblem(p);
      } catch (e: unknown) {
        if (!cancelled)
          setLoadError(e instanceof Error ? e.message : "Failed to load problem");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [problemId]);

  const appendConsole = useCallback((s: string) => {
    setConsoleText((prev) => (prev ? `${prev}\n${s}` : s));
  }, []);

  const fetchHint = useCallback(
    async (idx: number) => {
      try {
        const sourceParam = isDsa ? "&source=dsa" : "";
        const h = await apiGet<{ hint: string }>(
          `/coding/interview/hint?problem_id=${encodeURIComponent(problemId)}&hint_index=${idx}${sourceParam}`
        );
        setHintCard(h.hint);
      } catch {
        /* ignore */
      }
    },
    [problemId, isDsa]
  );

  useEffect(() => {
    const tick = () => {
      const now = Date.now();
      const idleMs = now - lastKeyAtRef.current;
      const empty = code.trim().length === 0;
      if (!empty) return;
      if (idleMs >= 120_000 && hintLevelRef.current === 0) {
        hintLevelRef.current = 1;
        void fetchHint(0);
      } else if (idleMs >= 120_000 + 90_000 && hintLevelRef.current === 1) {
        hintLevelRef.current = 2;
        void fetchHint(1);
      } else if (hintLevelRef.current >= 2) {
        const extra = Math.floor((idleMs - 120_000 - 90_000) / 90_000);
        const want = 2 + extra;
        if (want > hintLevelRef.current - 1) {
          hintLevelRef.current = want + 1;
          void fetchHint(Math.min(want, 20));
        }
      }
    };
    idleTimerRef.current = setInterval(tick, 5000);
    return () => {
      if (idleTimerRef.current) clearInterval(idleTimerRef.current);
    };
  }, [code, fetchHint]);

  const onEditorMount = useCallback(() => {
    lastKeyAtRef.current = Date.now();
  }, []);

  const handleRun = async () => {
    setBusy(true);
    setConsoleText("");
    try {
      const res = await apiPost<{ results: RunResultRow[] }>("/coding/interview/run", {
        problem_id: problemId,
        source_code: code,
        language_id: lang,
        session_id: sessionId,
        source: isDsa ? "dsa" : "",
      });
      const results = res.results || [];
      const passed = results.filter((r) => r.passed).length;
      const sig = JSON.stringify(results.map((r) => ({ p: r.passed, i: r.stdin })));
      if (sig === lastRunSigRef.current) runRepeatRef.current += 1;
      else runRepeatRef.current = 1;
      lastRunSigRef.current = sig;

      for (const r of results) {
        appendConsole(
          `[${r.passed ? "PASS" : "FAIL"}] in=${JSON.stringify(r.stdin)} out=${JSON.stringify(r.stdout)} exp=${JSON.stringify(r.expected)} time=${String(r.time)}`
        );
      }
      appendConsole(`Summary: ${passed}/${results.length} passed.`);

      const allFail = results.length > 0 && passed === 0;
      const repeatFail = runRepeatRef.current >= 2 && passed < results.length;
      if (allFail || repeatFail) {
        try {
          const a = await apiPost<{ tier: number; message: string }>(
            "/coding/interview/analyze",
            {
              problem_id: problemId,
              source_code: code,
              failed_test_cases: results.filter((r) => !r.passed),
              tier: 2,
              source: isDsa ? "dsa" : "",
            }
          );
          setHintCard(a.message);
        } catch {
          /* ignore */
        }
      }
    } catch (e: unknown) {
      appendConsole(e instanceof Error ? e.message : "Run failed");
    } finally {
      setBusy(false);
    }
  };

  const handleSubmit = async () => {
    setBusy(true);
    setScoring(null);
    const elapsed = Math.max(0, (Date.now() - startedAtRef.current) / 1000);
    try {
      const s = await apiPost<ScoringPayload>("/coding/interview/submit", {
        problem_id: problemId,
        source_code: code,
        language_id: lang,
        session_id: sessionId,
        time_taken_seconds: elapsed,
        source: isDsa ? "dsa" : "",
      });
      setScoring(s);
      appendConsole(
        `SCORE: ${s.correctness.passed}/${s.correctness.total} · quality ${s.quality.score} · ${s.complexity.time} time`
      );

      const total = s.correctness.total;
      const ok = s.correctness.passed === total;
      if (ok && s.complexity.is_optimal === false) {
        try {
          const a = await apiPost<{ message: string }>("/coding/interview/analyze", {
            problem_id: problemId,
            source_code: code,
            failed_test_cases: [],
            runtimes: s.empirical_ms,
            tier: 3,
            source: isDsa ? "dsa" : "",
          });
          setHintCard(a.message);
        } catch {
          /* ignore */
        }
      }

      onDebriefRequest?.(s);
    } catch (e: unknown) {
      appendConsole(e instanceof Error ? e.message : "Submit failed");
    } finally {
      setBusy(false);
    }
  };

  if (loadError) {
    return (
      <div className="rounded-xl border border-red-400/40 bg-red-950/40 p-6 text-sm">
        {loadError}
      </div>
    );
  }

  if (!problem) {
    return (
      <div className="rounded-xl border border-white/20 bg-white/5 p-8 text-center text-qace-muted">
        Loading problem…
      </div>
    );
  }

  const topics =
    Array.isArray(problem.topics) && problem.topics.length
      ? (problem.topics as string[]).join(", ")
      : "—";

  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col gap-4 p-4 md:flex-row md:p-6">
      <div className="card-glow flex w-full flex-col rounded-2xl border border-white/20 bg-white/5 p-5 md:max-w-xl md:flex-shrink-0">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-emerald-500/20 px-3 py-1 text-xs font-medium capitalize text-emerald-200">
            {problem.difficulty}
          </span>
          <span className="text-xs text-qace-muted">{topics}</span>
        </div>
        <h1 className="font-heading text-xl font-semibold">{problem.title}</h1>
        <div className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-white/90">
          {problem.description}
        </div>
        {Array.isArray(problem.examples) && problem.examples.length > 0 ? (
          <div className="mt-4 space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-qace-muted">Examples</p>
            {(problem.examples as { input?: string; output?: string }[]).map((ex, i) => {
              // neenza stores the full formatted text in `input`; try to split on Output: if present
              const raw = ex.input ?? "";
              const outputMarker = raw.indexOf("\nOutput:");
              const inputPart = outputMarker !== -1 ? raw.slice(0, outputMarker).trim() : raw.trim();
              const outputPart = outputMarker !== -1 ? raw.slice(outputMarker + 1).trim() : (ex.output ?? "");
              return (
                <div key={i} className="rounded-xl bg-black/30 p-3 text-xs font-mono">
                  <p className="mb-1 font-sans text-[10px] font-semibold uppercase tracking-wider text-qace-muted">
                    Example {i + 1}
                  </p>
                  <p className="whitespace-pre-wrap text-white/80">{inputPart}</p>
                  {outputPart && (
                    <p className="mt-1 whitespace-pre-wrap text-emerald-300">{outputPart}</p>
                  )}
                </div>
              );
            })}
          </div>
        ) : null}
        {problem.constraints ? (
          <div className="mt-3 text-sm text-qace-muted">
            <span className="font-medium text-white/80">Constraints: </span>
            {problem.constraints}
          </div>
        ) : null}
        {onClose ? (
          <button
            type="button"
            onClick={onClose}
            className="mt-6 rounded-xl border border-white/20 px-4 py-2 text-sm hover:bg-white/10"
          >
            Close coding round
          </button>
        ) : null}
      </div>

      <div className="flex min-h-[480px] flex-1 flex-col gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={lang}
            onChange={(e) => setLang(Number(e.target.value))}
            className="rounded-lg border border-white/20 bg-black/40 px-3 py-2 text-sm"
          >
            {LANGS.map((l) => (
              <option key={l.id} value={l.id}>
                {l.label}
              </option>
            ))}
          </select>
          {/* Elapsed timer */}
          <span className="ml-auto font-mono text-sm tabular-nums text-qace-muted">
            {String(Math.floor(elapsed / 60)).padStart(2, "0")}:{String(elapsed % 60).padStart(2, "0")}
          </span>
          <button
            type="button"
            disabled={busy}
            onClick={() => void handleRun()}
            className="rounded-xl bg-white/15 px-4 py-2 text-sm font-medium hover:bg-white/25 disabled:opacity-50"
          >
            Run
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void handleSubmit()}
            className="rounded-xl bg-gradient-to-r from-qace-accent to-qace-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            Submit
          </button>
        </div>

        <div className="min-h-[280px] flex-1 overflow-hidden rounded-xl border border-white/20">
          <Editor
            height="100%"
            defaultLanguage="python"
            theme="vs-dark"
            value={code}
            onChange={(v) => {
              setCode(v ?? "");
              lastKeyAtRef.current = Date.now();
            }}
            onMount={onEditorMount}
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              scrollBeyondLastLine: false,
            }}
          />
        </div>

        {hintCard ? (
          <div className="rounded-xl border border-amber-400/40 bg-amber-950/30 px-4 py-3 text-sm text-amber-100">
            {hintCard}
          </div>
        ) : null}

        {scoring ? (
          <div className="rounded-xl border border-emerald-400/30 bg-emerald-950/20 p-4 text-sm">
            <p className="font-semibold text-emerald-200">Scoring summary</p>
            <p className="mt-1 text-white/90">
              Correctness: {scoring.correctness.passed}/{scoring.correctness.total}
            </p>
            <p className="text-white/90">
              Complexity: {scoring.complexity.time} time, {scoring.complexity.space}{" "}
              space
              {scoring.complexity.is_optimal ? " (optimal)" : ` (target ${scoring.complexity.optimal})`}
            </p>
            <p className="mt-1 text-qace-muted">{scoring.complexity.explanation}</p>
            <p className="mt-2 text-white/90">
              Quality score: {scoring.quality.score}
            </p>
            <ul className="mt-1 list-inside list-disc text-xs text-qace-muted">
              {(scoring.quality.observations || []).map((o, i) => (
                <li key={i}>{o}</li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className="max-h-48 overflow-auto rounded-xl border border-white/15 bg-black/50 p-3 font-mono text-xs text-qace-muted">
          {consoleText || "Console output…"}
        </div>
      </div>
    </div>
  );
}
