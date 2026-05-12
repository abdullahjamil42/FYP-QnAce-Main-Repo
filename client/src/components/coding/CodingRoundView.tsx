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
  source?: "dsa" | "supabase";
};

// ── Multi-language support ──
const LANGS: { id: number; label: string }[] = [
  { id: 71, label: "Python 3" },
  { id: 63, label: "JavaScript" },
  { id: 62, label: "Java" },
  { id: 54, label: "C++ (g++17)" },
];

const LANG_MONACO: Record<number, string> = {
  71: "python",
  63: "javascript",
  62: "java",
  54: "cpp",
};

const LANG_STARTERS: Record<number, string> = {
  71: 'name = input().strip()\nprint(f"Hello, {name}")\n',
  63: 'const lines = require("fs").readFileSync("/dev/stdin","utf8").trim().split("\\n");\nconsole.log(lines[0]);\n',
  62: 'import java.util.Scanner;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    System.out.println(sc.nextLine());\n  }\n}\n',
  54: '#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n  string s; getline(cin,s);\n  cout<<s<<endl;\n}\n',
};

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

type AttemptEntry = {
  code: string;
  lang: number;
  passed: boolean;
  passedCount: number;
  totalCount: number;
  timestamp: number;
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
  hidden_summary?: { total_hidden: number; passed_hidden: number };
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
  const [code, setCode] = useState(LANG_STARTERS[71]);
  const [lang, setLang] = useState(71);

  // ── Console tabs ──
  const [activeConsoleTab, setActiveConsoleTab] = useState<"output" | "custom">("output");
  const [consoleText, setConsoleText] = useState("");
  const [customInput, setCustomInput] = useState("");
  const [customResult, setCustomResult] = useState("");
  const [customBusy, setCustomBusy] = useState(false);

  const [hintCard, setHintCard] = useState<string | null>(null);
  const [scoring, setScoring] = useState<ScoringPayload | null>(null);
  const [busy, setBusy] = useState(false);

  // ── Attempt history ──
  const [attempts, setAttempts] = useState<AttemptEntry[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  // ── Run-state for smarter hint gating ──
  const [hasRun, setHasRun] = useState(false);
  const [lastRunHadFailures, setLastRunHadFailures] = useState(false);
  const hintsOffRef = useRef(false);

  // ── Timer: reading vs coding ──
  const [elapsed, setElapsed] = useState(0);
  const [readingSeconds, setReadingSeconds] = useState<number | null>(null);
  const [firstKeystrokeAt, setFirstKeystrokeAt] = useState<number | null>(null);
  const problemLoadedAtRef = useRef<number>(Date.now());
  const startedAtRef = useRef<number>(Date.now());
  const lastKeyAtRef = useRef<number>(Date.now());
  const hintLevelRef = useRef(0);
  const idleTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastRunSigRef = useRef<string>("");
  const runRepeatRef = useRef(0);

  // ── Elapsed timer (counts from problem load) ──
  useEffect(() => {
    problemLoadedAtRef.current = Date.now();
    startedAtRef.current = Date.now();
    setElapsed(0);
    setFirstKeystrokeAt(null);
    setReadingSeconds(null);
    hintLevelRef.current = 0;
    hintsOffRef.current = false;
    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAtRef.current) / 1000));
    }, 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [problemId]);

  // ── Load problem (source derived from API response, not URL param) ──
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        // Try DSA endpoint first; if it 404s fall back to Supabase
        let p: ProblemPayload | null = null;
        try {
          p = await apiGet<ProblemPayload>(`/coding/dsa/problems/${problemId}`);
        } catch {
          p = await apiGet<ProblemPayload>(`/coding/problems/${problemId}`);
        }
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

  const prettyConsoleValue = useCallback((v?: string) => {
    const text = String(v ?? "");
    return text.trim().length ? text : "<empty>";
  }, []);

  const isDsa = problem?.source === "dsa";

  const fetchHint = useCallback(
    async (idx: number) => {
      if (hintsOffRef.current) return;
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

  // ── Hint gating: only trigger if user has run code and still has failures ──
  useEffect(() => {
    const tick = () => {
      if (hintsOffRef.current) return;
      const now = Date.now();
      const idleMs = now - lastKeyAtRef.current;
      // Gate 1: must have run at least once with failures; OR editor is empty
      const empty = code.trim().length === 0;
      const shouldHint = empty || (hasRun && lastRunHadFailures);
      if (!shouldHint) return;
      if (idleMs >= 120_000 && hintLevelRef.current === 0) {
        hintLevelRef.current = 1;
        void fetchHint(0);
      } else if (idleMs >= 210_000 && hintLevelRef.current === 1) {
        hintLevelRef.current = 2;
        void fetchHint(1);
      } else if (hintLevelRef.current >= 2) {
        const extra = Math.floor((idleMs - 210_000) / 90_000);
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
  }, [code, fetchHint, hasRun, lastRunHadFailures]);

  const recordFirstKeystroke = useCallback(() => {
    if (firstKeystrokeAt === null) {
      const now = Date.now();
      setFirstKeystrokeAt(now);
      setReadingSeconds(Math.round((now - problemLoadedAtRef.current) / 1000));
    }
    lastKeyAtRef.current = Date.now();
  }, [firstKeystrokeAt]);

  const onEditorMount = useCallback(() => {
    lastKeyAtRef.current = Date.now();
  }, []);

  // ── Language switch: reset code to starter ──
  const handleLangChange = (newLang: number) => {
    setLang(newLang);
    setCode(LANG_STARTERS[newLang] ?? "");
  };

  const handleRun = async () => {
    setBusy(true);
    setConsoleText("");
    setActiveConsoleTab("output");
    try {
      const res = await apiPost<{ results: RunResultRow[] }>("/coding/interview/run", {
        problem_id: problemId,
        source_code: code,
        language_id: lang,
        session_id: sessionId,
        source: isDsa ? "dsa" : "",
      });
      const results = res.results || [];
      const passedCount = results.filter((r) => r.passed).length;
      const hadFailures = passedCount < results.length;
      setHasRun(true);
      setLastRunHadFailures(hadFailures);

      const sig = JSON.stringify(results.map((r) => ({ p: r.passed, i: r.stdin })));
      if (sig === lastRunSigRef.current) runRepeatRef.current += 1;
      else runRepeatRef.current = 1;
      lastRunSigRef.current = sig;

      // Push attempt
      setAttempts((prev) => [
        ...prev,
        {
          code,
          lang,
          passed: !hadFailures,
          passedCount,
          totalCount: results.length,
          timestamp: Date.now(),
        },
      ]);

      for (let i = 0; i < results.length; i += 1) {
        const r = results[i];
        appendConsole(`Test ${i + 1}: ${r.passed ? "PASS" : "FAIL"}`);
        appendConsole(`Input:\n${prettyConsoleValue(r.stdin)}`);
        if ((r.stderr ?? "").trim().length > 0) {
          appendConsole(`Error:\n${prettyConsoleValue(r.stderr)}`);
        } else {
          appendConsole(`Output:\n${prettyConsoleValue(r.stdout)}`);
        }
        if (!r.passed) appendConsole(`Expected:\n${prettyConsoleValue(r.expected)}`);
        appendConsole(`Time: ${String(r.time ?? "n/a")}s`);
        if (i < results.length - 1) appendConsole("---");
      }
      appendConsole(`Summary: ${passedCount}/${results.length} passed.`);

      const allFail = results.length > 0 && passedCount === 0;
      const repeatFail = runRepeatRef.current >= 2 && hadFailures;
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
              attempts: attempts.slice(-3),
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

  const handleCustomRun = async () => {
    setCustomBusy(true);
    setCustomResult("");
    try {
      const res = await apiPost<{ results: RunResultRow[] }>("/coding/interview/run", {
        problem_id: problemId,
        source_code: code,
        language_id: lang,
        session_id: sessionId,
        source: isDsa ? "dsa" : "",
        custom_stdin: customInput,
      });
      const r = res.results?.[0];
      if (r) {
        if ((r.stderr ?? "").trim()) {
          setCustomResult(`Error:\n${r.stderr}`);
        } else {
          setCustomResult(r.stdout || "<empty>");
        }
      }
    } catch (e: unknown) {
      setCustomResult(e instanceof Error ? e.message : "Run failed");
    } finally {
      setCustomBusy(false);
    }
  };

  const handleSubmit = async () => {
    setBusy(true);
    setScoring(null);
    hintsOffRef.current = true; // stop hints after submit
    const nowMs = Date.now();
    const totalSeconds = Math.max(0, (nowMs - startedAtRef.current) / 1000);
    const codingSeconds = firstKeystrokeAt
      ? Math.max(0, (nowMs - firstKeystrokeAt) / 1000)
      : totalSeconds;
    const readingSec = readingSeconds ?? 0;
    try {
      const s = await apiPost<ScoringPayload>("/coding/interview/submit", {
        problem_id: problemId,
        source_code: code,
        language_id: lang,
        session_id: sessionId,
        time_taken_seconds: totalSeconds,
        reading_time_seconds: readingSec,
        coding_time_seconds: codingSeconds,
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
            attempts: attempts.slice(-3),
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

  // Phase label
  const phaseLabel = firstKeystrokeAt === null ? "Reading" : "Coding";

  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col gap-4 p-4 md:flex-row md:p-6">
      {/* ── Problem panel ── */}
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

      {/* ── Editor + console panel ── */}
      <div className="flex min-h-[480px] flex-1 flex-col gap-3">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={lang}
            onChange={(e) => handleLangChange(Number(e.target.value))}
            className="rounded-lg border border-white/20 bg-black/40 px-3 py-2 text-sm"
          >
            {LANGS.map((l) => (
              <option key={l.id} value={l.id}>
                {l.label}
              </option>
            ))}
          </select>

          {/* Phase + elapsed timer */}
          <span className="ml-auto font-mono text-sm tabular-nums text-qace-muted">
            <span className="mr-1 text-xs text-white/40">{phaseLabel}</span>
            {String(Math.floor(elapsed / 60)).padStart(2, "0")}:{String(elapsed % 60).padStart(2, "0")}
          </span>

          {/* History button */}
          {attempts.length > 0 && (
            <button
              type="button"
              onClick={() => setShowHistory((v) => !v)}
              className="rounded-xl border border-white/20 px-3 py-2 text-xs hover:bg-white/10"
            >
              History ({attempts.length})
            </button>
          )}

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

        {/* History panel */}
        {showHistory && (
          <div className="rounded-xl border border-white/15 bg-black/40 p-3 text-xs">
            <p className="mb-2 font-semibold text-white/70">Attempt history</p>
            <div className="space-y-1">
              {attempts.map((a, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className={`font-mono ${a.passed ? "text-emerald-400" : "text-red-400"}`}>
                    #{i + 1}
                  </span>
                  <span className="text-qace-muted">
                    {a.passedCount}/{a.totalCount} · {LANGS.find((l) => l.id === a.lang)?.label}
                  </span>
                  <button
                    type="button"
                    onClick={() => { setCode(a.code); setLang(a.lang); setShowHistory(false); }}
                    className="ml-auto rounded px-2 py-0.5 text-[10px] border border-white/20 hover:bg-white/10"
                  >
                    Restore
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Monaco editor */}
        <div className="min-h-[280px] flex-1 overflow-hidden rounded-xl border border-white/20">
          <Editor
            height="100%"
            language={LANG_MONACO[lang] ?? "python"}
            theme="vs-dark"
            value={code}
            onChange={(v) => {
              setCode(v ?? "");
              recordFirstKeystroke();
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
            {scoring.hidden_summary && scoring.hidden_summary.total_hidden > 0 && (
              <p className="text-white/70 text-xs">
                Hidden tests: {scoring.hidden_summary.passed_hidden}/{scoring.hidden_summary.total_hidden} passed
              </p>
            )}
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

        {/* Console tabs */}
        <div className="rounded-xl border border-white/15 bg-black/50">
          <div className="flex border-b border-white/10">
            <button
              type="button"
              onClick={() => setActiveConsoleTab("output")}
              className={`px-4 py-2 text-xs font-medium ${activeConsoleTab === "output" ? "text-white border-b-2 border-qace-accent" : "text-qace-muted"}`}
            >
              Output
            </button>
            <button
              type="button"
              onClick={() => setActiveConsoleTab("custom")}
              className={`px-4 py-2 text-xs font-medium ${activeConsoleTab === "custom" ? "text-white border-b-2 border-qace-accent" : "text-qace-muted"}`}
            >
              Custom input
            </button>
          </div>
          {activeConsoleTab === "output" ? (
            <div className="max-h-48 overflow-auto p-3 font-mono text-xs text-qace-muted">
              {consoleText || "Console output…"}
            </div>
          ) : (
            <div className="p-3 space-y-2">
              <textarea
                value={customInput}
                onChange={(e) => setCustomInput(e.target.value)}
                placeholder="Enter custom stdin…"
                rows={3}
                className="w-full rounded-lg bg-black/40 border border-white/15 p-2 font-mono text-xs text-white resize-none focus:outline-none"
              />
              <button
                type="button"
                disabled={customBusy}
                onClick={() => void handleCustomRun()}
                className="rounded-lg bg-white/10 px-3 py-1 text-xs hover:bg-white/20 disabled:opacity-50"
              >
                {customBusy ? "Running…" : "Run with custom input"}
              </button>
              {customResult && (
                <pre className="mt-2 max-h-32 overflow-auto rounded-lg bg-black/40 p-2 font-mono text-xs text-white/80 whitespace-pre-wrap">
                  {customResult}
                </pre>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

