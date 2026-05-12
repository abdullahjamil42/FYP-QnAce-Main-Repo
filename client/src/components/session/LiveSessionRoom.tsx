"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useDataChannel, type PerceptionEvent, type TranscriptEvent } from "@/hooks/useDataChannel";
import { useWebRTC } from "@/hooks/useWebRTC";
import VideoCanvas from "@/components/VideoCanvas";
import CodingRoundView from "@/components/coding/CodingRoundView";
import { loadSetupConfig, persistSession } from "@/lib/interview-session-store";
import { jobRoles } from "@/lib/mock-data";

// ── Module-level constants ──────────────────────────────────────────────────
const EMOTION_SENTIMENT: Record<string, number> = {
  excellent: 95, confident: 88, composed: 82, engaged: 78, happy: 80,
  positive: 80, good: 75, neutral: 50, average: 45,
  uncertain: 30, nervous: 28, anxious: 22, stressed: 15, poor: 12,
};

const SCORE_CRITERIA: Record<string, string[]> = {
  Content:  ["Relevance to question", "Technical depth", "Answer structure", "Use of examples"],
  Delivery: ["Speaking pace (WPM)", "Clarity of diction", "Filler word frequency", "Confidence markers"],
  Composure:["Pause frequency", "Hesitation patterns", "Vocal stability", "Emotional consistency"],
};

const EMOTION_COLORS: Record<string, { bg: string; text: string; ring: string; dot: string }> = {
  confident: { bg: "bg-emerald-500/20", text: "text-emerald-200", ring: "ring-emerald-400", dot: "#34d399" },
  composed:  { bg: "bg-emerald-500/20", text: "text-emerald-200", ring: "ring-emerald-400", dot: "#34d399" },
  engaged:   { bg: "bg-blue-500/20",    text: "text-blue-200",    ring: "ring-blue-400",    dot: "#60a5fa" },
  happy:     { bg: "bg-yellow-500/20",  text: "text-yellow-200",  ring: "ring-yellow-400",  dot: "#fbbf24" },
  positive:  { bg: "bg-emerald-500/20", text: "text-emerald-200", ring: "ring-emerald-400", dot: "#34d399" },
  good:      { bg: "bg-emerald-500/20", text: "text-emerald-200", ring: "ring-emerald-400", dot: "#34d399" },
  excellent: { bg: "bg-sky-500/20",     text: "text-sky-200",     ring: "ring-sky-400",     dot: "#38bdf8" },
  neutral:   { bg: "bg-slate-500/20",   text: "text-slate-200",   ring: "ring-slate-400",   dot: "#94a3b8" },
  average:   { bg: "bg-slate-500/20",   text: "text-slate-200",   ring: "ring-slate-400",   dot: "#94a3b8" },
  uncertain: { bg: "bg-amber-500/20",   text: "text-amber-200",   ring: "ring-amber-400",   dot: "#f59e0b" },
  nervous:   { bg: "bg-amber-500/20",   text: "text-amber-200",   ring: "ring-amber-400",   dot: "#f59e0b" },
  anxious:   { bg: "bg-amber-500/20",   text: "text-amber-200",   ring: "ring-amber-400",   dot: "#f59e0b" },
  stressed:  { bg: "bg-red-500/20",     text: "text-red-200",     ring: "ring-red-400",     dot: "#f87171" },
  poor:      { bg: "bg-red-500/20",     text: "text-red-200",     ring: "ring-red-400",     dot: "#f87171" },
};
const EMOTION_DEFAULT_COLORS = { bg: "bg-slate-500/20", text: "text-slate-200", ring: "ring-slate-400", dot: "#94a3b8" };
// ────────────────────────────────────────────────────────────────────────────

export default function LiveSessionRoom() {
  const router = useRouter();
  const sp = useSearchParams();
  const {
    state,
    error,
    sessionId,
    dataChannel,
    auChannel,
    webcamStream,
    remoteAudioStream,
    remoteVideoStream,
    isMicEnabled,
    isCamEnabled,
    toggleMic,
    toggleCam,
    start,
    stop,
    addVideoTrack,
  } = useWebRTC();
  const {
    transcripts,
    scores,
    perception,
    statusLog,
    currentPhase,
    currentQuestion,
    questionHistory,
    interviewEnd,
    latestTranscript,
    codingStart,
    sendCommand,
    sendCodingDebrief,
    clearTranscripts,
    sendAUTelemetry,
  } = useDataChannel(dataChannel, auChannel);

  const startedAtRef = useRef<string | null>(null);
  const isSavingRef = useRef(false);
  const [showTranscriptPanel, setShowTranscriptPanel] = useState(true);
  const [countdown, setCountdown] = useState<number>(0);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [perceptionHistory, setPerceptionHistory] = useState<{ vocal: number[]; face: number[]; tone: number[] }>({ vocal: [], face: [], tone: [] });
  const [autoScrollPaused, setAutoScrollPaused] = useState(false);
  const transcriptScrollRef = useRef<HTMLDivElement>(null);

  const isConnected = state === "connected";
  const isConnecting = state === "connecting";

  const ttsAudioRef = useRef<HTMLAudioElement>(null);

  const setup = loadSetupConfig();
  const roleName = jobRoles.find((r) => r.id === setup.jobRole)?.title ?? "Interview";

  // Phase label (no countdown needed)
  useEffect(() => {
    // No timer — phases are unlimited
  }, [currentPhase]);

  useEffect(() => {
    const audioEl = ttsAudioRef.current;
    if (!audioEl) return;

    if (!remoteAudioStream) {
      audioEl.pause();
      audioEl.srcObject = null;
      return;
    }

    audioEl.autoplay = true;
    audioEl.setAttribute("playsinline", "true");
    audioEl.muted = false;
    audioEl.srcObject = remoteAudioStream;

    const startPlayback = () => {
      void audioEl.play().catch((err) => {
        console.warn("Remote TTS playback was blocked:", err);
      });
    };

    audioEl.onloadedmetadata = startPlayback;
    startPlayback();

    return () => {
      audioEl.onloadedmetadata = null;
    };
  }, [remoteAudioStream]);

  const handleFaceCropStream = useCallback(
    (stream: MediaStream) => {
      addVideoTrack(stream);
    },
    [addVideoTrack]
  );

  useEffect(() => {
    if (state === "connected" && !startedAtRef.current) {
      startedAtRef.current = new Date().toISOString();
    }
  }, [state]);

  const handleStart = useCallback(() => {
    clearTranscripts();
    if (!startedAtRef.current) {
      startedAtRef.current = new Date().toISOString();
    }
    const cfg = loadSetupConfig();
    void start({ jobRole: cfg.jobRole, interviewType: cfg.interviewType });
  }, [clearTranscripts, start]);

  const handleBackToLobby = useCallback(() => {
    if (!confirm("Leave the interview and return to the lobby?")) return;
    stop();
    clearTranscripts();
    startedAtRef.current = null;
    router.push("/session/lobby");
  }, [stop, clearTranscripts, router]);

  const handleDropCall = useCallback(() => {
    stop();
    clearTranscripts();
    startedAtRef.current = null;
  }, [clearTranscripts, stop]);

  const handleTranscriptScroll = useCallback(() => {
    const el = transcriptScrollRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop <= el.clientHeight + 24;
    setAutoScrollPaused(!atBottom);
  }, []);

  const handleStopAndSave = useCallback(async () => {
    if (isSavingRef.current) return;
    isSavingRef.current = true;

    const cfg = loadSetupConfig();
    const startTime = startedAtRef.current ?? new Date().toISOString();
    const endTime = new Date().toISOString();

    try {
      const saved = await persistSession({
        mode: cfg.mode,
        difficulty: cfg.difficulty,
        durationMinutes: cfg.durationMinutes,
        startedAt: startTime,
        endedAt: endTime,
        status: "completed",
        scores,
        transcripts,
        perception,
        webrtcSessionId: sessionId,
        perQuestionScores: interviewEnd?.per_question_scores ?? [],
        avgTotalScore: interviewEnd?.avg_total_score,
      });
      stop();
      router.push(`/session/summary?sessionId=${saved.id}`);
    } catch {
      stop();
      router.push("/session/summary");
    } finally {
      isSavingRef.current = false;
      startedAtRef.current = null;
    }
  }, [interviewEnd, perception, router, scores, sessionId, stop, transcripts]);

  // Auto-navigate to summary when interview ends
  useEffect(() => {
    if (interviewEnd && isConnected) {
      const timer = setTimeout(() => {
        void handleStopAndSave();
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [interviewEnd, isConnected, handleStopAndSave]);

  // Rolling perception history for sparklines
  useEffect(() => {
    if (!perception) return;
    const toScore = (e: string) => EMOTION_SENTIMENT[e.toLowerCase()] ?? 50;
    setPerceptionHistory((prev) => ({
      vocal: [...prev.vocal, toScore(perception.vocal_emotion)].slice(-30),
      face:  [...prev.face,  toScore(perception.face_emotion)].slice(-30),
      tone:  [...prev.tone,  toScore(perception.text_quality_label)].slice(-30),
    }));
  }, [perception]);

  // Auto-scroll transcript container (not the page)
  useEffect(() => {
    if (!autoScrollPaused) {
      const el = transcriptScrollRef.current;
      if (el) el.scrollTop = el.scrollHeight;
    }
  }, [transcripts, autoScrollPaused]);

  const phaseLabel = currentPhase?.phase ?? "idle";
  const isThinking = phaseLabel === "thinking";
  const isAnswering = phaseLabel === "answering";
  const isComplete = phaseLabel === "complete";
  const questionIndex = currentQuestion?.index ?? -1;
  const totalQuestions = currentQuestion?.total ?? 0;
  const currentVoice = currentQuestion?.voice ?? "male";

  // URL-param coding round (manual/legacy) or server-authoritative (data-channel)
  const urlCodingProblemId = sp.get("problemId") || "";
  const serverCodingProblemId = codingStart?.problem_id ?? "";
  const codingProblemId = serverCodingProblemId || urlCodingProblemId;
  const showCodingOverlay =
    codingProblemId.length > 0 &&
    Boolean(sessionId) &&
    (Boolean(codingStart) || (sp.get("coding") === "1" && urlCodingProblemId.length > 0));

  return (
    <>
    <main className="min-h-screen bg-gradient-to-b from-[#0b1225] via-[#0d152d] to-[#091024] p-4 text-qace-text lg:p-6">
      {/* Header */}
      <header className="card-glow mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/20 bg-white/5 px-4 py-3 shadow-xl shadow-black/20">
        <div className="flex items-center gap-3">
          <button
            onClick={handleBackToLobby}
            className="rounded-lg border border-white/10 bg-white/5 p-1.5 text-qace-muted transition hover:bg-white/10 hover:text-white"
            title="Back to Lobby"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <p className="text-xs uppercase tracking-wide text-qace-muted">Q&Ace Live Interview Room</p>
            <h1 className="text-xl font-semibold">{roleName} Mock Interview</h1>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {questionIndex >= 0 && (
            <span className="rounded-full bg-indigo-500/20 px-2.5 py-1 font-medium text-indigo-200">
              Q{questionIndex + 1} / {totalQuestions}
            </span>
          )}
          <span className={`rounded-full px-2.5 py-1 font-medium ${currentVoice === "female"
              ? "bg-pink-500/20 text-pink-200"
              : "bg-blue-500/20 text-blue-200"
            }`}>
            Interviewer {currentVoice === "female" ? "2 (F)" : "1 (M)"}
          </span>
          <span className={`rounded-full px-2.5 py-1 font-medium ${isConnected
              ? "bg-emerald-500/25 text-emerald-200"
              : isConnecting
                ? "bg-amber-500/25 text-amber-100"
                : "bg-slate-500/25 text-slate-200"
            }`}>
            {state}
          </span>
          {sessionId ? (
            <span className="rounded-full bg-black/30 px-2.5 py-1 text-qace-muted">ID {sessionId.slice(0, 8)}</span>
          ) : null}
        </div>
      </header>

      {/* Phase Bar */}
      {isConnected && phaseLabel !== "idle" && (
        <div className={`mb-4 flex items-center justify-between rounded-2xl border px-4 py-3 text-sm transition-colors ${isAnswering
            ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-100"
            : isComplete
              ? "border-indigo-400/30 bg-indigo-500/10 text-indigo-100"
              : phaseLabel === "transition"
                ? "border-purple-400/30 bg-purple-500/10 text-purple-100"
                : phaseLabel === "speaking"
                  ? "border-blue-400/30 bg-blue-500/10 text-blue-100"
                  : "border-white/10 bg-white/5 text-qace-muted"
          }`}>
          <div className="flex items-center gap-3">
            <span className={`h-2.5 w-2.5 rounded-full ${isAnswering ? "bg-emerald-400 animate-pulse"
                : phaseLabel === "speaking" ? "bg-blue-400 animate-pulse"
                  : "bg-indigo-400"
              }`} />
            <span className="font-semibold capitalize">
              {isAnswering
                ? "Your Turn — Speak now"
                : phaseLabel === "speaking"
                  ? "Interviewer Speaking..."
                  : phaseLabel === "transition"
                    ? "Moving to next question..."
                    : phaseLabel}
            </span>
          </div>
        </div>
      )}

      {error ? (
        <div className="mb-4 rounded-xl border border-red-400/30 bg-red-500/15 p-3 text-sm text-red-100">
          <strong>Error:</strong> {error}
        </div>
      ) : null}

      {/* Interview Complete Banner */}
      {interviewEnd && (
        <div className="mb-4 rounded-2xl border border-indigo-400/30 bg-indigo-500/10 p-4 text-center">
          <p className="text-lg font-semibold text-indigo-100">Interview Complete</p>
          <p className="mt-1 text-sm text-indigo-200/80">
            {interviewEnd.answered} answered, {interviewEnd.skipped} skipped out of {interviewEnd.total_questions} questions
          </p>
          <p className="mt-2 text-xs text-qace-muted">Saving session and redirecting to summary...</p>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-12">
        {/* Video Section */}
        <section className="lg:col-span-8">
          <div className="card-glow relative overflow-hidden rounded-3xl border border-white/20 bg-[#12182a] p-3 shadow-2xl shadow-black/35">
            <div className="absolute left-4 top-4 z-10 flex items-center gap-2 rounded-full bg-black/45 px-3 py-1 text-xs">
              <span className={`h-2 w-2 rounded-full ${isConnected ? "bg-red-400 animate-pulse" : "bg-slate-400"}`} />
              <span>{isConnected ? "Live Recording" : "Not Connected"}</span>
            </div>

            <audio ref={ttsAudioRef} autoPlay playsInline className="hidden" />

            {webcamStream ? (
              <VideoCanvas
                videoStream={webcamStream}
                onFaceCropStream={handleFaceCropStream}
                onAUTelemetry={sendAUTelemetry}
                showOverlay={true}
                showStats={false}
                containerClassName="w-full"
                videoClassName="h-[420px] w-full rounded-2xl"
              />
            ) : (
              <div className="flex h-[420px] w-full items-center justify-center rounded-2xl bg-qace-surface text-6xl">
                {isConnected ? "🎥" : "📷"}
              </div>
            )}

            {/* AI Interviewer Avatar PiP */}
            <div className="card-glow absolute right-6 top-6 z-10 w-52 rounded-2xl border border-white/20 bg-black/30 backdrop-blur-sm">
              <AIAvatarCard phase={phaseLabel} voice={currentVoice ?? "male"} />
              <div className="flex items-center justify-between border-t border-white/10 px-3 py-2 text-xs text-qace-muted">
                <span>Interviewer {currentVoice === "female" ? "2" : "1"}</span>
                <span className={currentVoice === "female" ? "text-pink-300" : "text-blue-300"}>
                  {currentVoice === "female" ? "♀ Female" : "♂ Male"}
                </span>
              </div>
            </div>

            {/* Controls */}
            <div className="card-glow mt-3 flex flex-wrap items-center justify-center gap-2 rounded-2xl border border-white/20 bg-black/25 px-3 py-3">
              <button
                onClick={handleStart}
                disabled={isConnected || isConnecting}
                className="rounded-full bg-emerald-500 px-5 py-2 text-sm font-semibold text-white transition hover:bg-emerald-400 disabled:opacity-40"
              >
                {isConnecting ? "Connecting..." : "Join Interview"}
              </button>
              <button
                onClick={toggleMic}
                disabled={!isConnected}
                className={`rounded-full px-5 py-2 text-sm font-semibold text-white transition disabled:opacity-40 ${isMicEnabled ? "bg-slate-700 hover:bg-slate-600" : "bg-amber-600 hover:bg-amber-500"
                  }`}
              >
                {isMicEnabled ? "Mic On" : "Mic Off"}
              </button>
              <button
                onClick={toggleCam}
                disabled={!isConnected || !webcamStream}
                className={`rounded-full px-5 py-2 text-sm font-semibold text-white transition disabled:opacity-40 ${isCamEnabled ? "bg-slate-700 hover:bg-slate-600" : "bg-amber-600 hover:bg-amber-500"
                  }`}
              >
                {isCamEnabled ? "Cam On" : "Cam Off"}
              </button>
              <button
                onClick={() => setShowTranscriptPanel((prev) => !prev)}
                className="rounded-full bg-indigo-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500"
              >
                {showTranscriptPanel ? "Hide Transcript" : "Show Transcript"}
              </button>
              <button
                onClick={handleDropCall}
                disabled={!isConnected}
                className="rounded-full bg-rose-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-rose-500 disabled:opacity-40"
              >
                Drop Call
              </button>
              <button
                onClick={handleStopAndSave}
                disabled={!isConnected}
                className="rounded-full bg-red-500 px-5 py-2 text-sm font-semibold text-white transition hover:bg-red-400 disabled:opacity-40"
              >
                End & Save
              </button>
            </div>
          </div>

          {/* Current Question Display */}
          {currentQuestion && currentQuestion.text && (
            <div className="card-glow mt-4 rounded-2xl border border-white/20 bg-white/5 p-4 shadow-xl shadow-black/20">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold">Current Question</h2>
                {currentQuestion.question_type === "dsa" && (
                  <span className="rounded-full bg-amber-500/20 px-2 py-1 text-xs text-amber-200">Coding</span>
                )}
              </div>
              <p className="mt-2 text-sm leading-relaxed">{currentQuestion.text}</p>
            </div>
          )}
        </section>

        {/* Sidebar */}
        <aside className="space-y-4 lg:col-span-4">
          {/* Scores */}
          <section className="card-glow rounded-2xl border border-white/20 bg-white/5 p-4 shadow-xl shadow-black/20">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold">Interview Intelligence</h2>
              <span className="rounded-full bg-qace-primary/20 px-2 py-1 text-xs text-indigo-200">AI Analysis</span>
            </div>
            {scores ? (
              <div className="space-y-3 text-sm">
                <RichScoreRow label="Content"  value={scores.content}  verdict={makeVerdict("Content",  scores.content,  perception, latestTranscript)} />
                <RichScoreRow label="Delivery" value={scores.delivery} verdict={makeVerdict("Delivery", scores.delivery, perception, latestTranscript)} />
                <RichScoreRow label="Composure" value={scores.composure} verdict={makeVerdict("Composure", scores.composure, perception, latestTranscript)} />
                <div className="card-glow rounded-xl border border-white/20 bg-black/20 px-3 py-2 text-center">
                  <div className="text-3xl font-semibold text-qace-accent">{scores.final.toFixed(1)}</div>
                  <div className="text-xs text-qace-muted">Weighted average · updated live</div>
                </div>
              </div>
            ) : (
              <p className="text-sm italic text-qace-muted">Start speaking to unlock score and coaching metrics.</p>
            )}
          </section>

          {/* Emotion Badges */}
          {perception && isConnected && (
            <section className="card-glow rounded-2xl border border-white/20 bg-white/5 p-4 shadow-xl shadow-black/20">
              <h2 className="mb-3 text-base font-semibold">Live Emotion</h2>
              <div className="space-y-2.5">
                <AnimatedEmotionBadge label="Voice" emotion={perception.vocal_emotion}      history={perceptionHistory.vocal} />
                <AnimatedEmotionBadge label="Face"  emotion={perception.face_emotion}       history={perceptionHistory.face} />
                <AnimatedEmotionBadge label="Tone"  emotion={perception.text_quality_label} history={perceptionHistory.tone} />
              </div>
            </section>
          )}

          {/* Question Progress */}
          <section className="card-glow rounded-2xl border border-white/20 bg-white/5 p-4 shadow-xl shadow-black/20">
            <h2 className="mb-3 text-base font-semibold">Question Progress</h2>
            {totalQuestions > 0 && (
              <div className="mb-3 flex gap-1">
                {Array.from({ length: totalQuestions }).map((_, i) => (
                  <div
                    key={i}
                    className={`h-2 flex-1 rounded-full transition-colors duration-300 ${
                      i < questionIndex
                        ? "bg-emerald-500/60"
                        : i === questionIndex
                          ? "bg-emerald-400 shadow-[0_0_6px_#34d399]"
                          : "bg-white/10"
                    }`}
                  />
                ))}
              </div>
            )}
            <div className="space-y-2 text-sm">
              {questionHistory.length === 0 ? (
                <p className="text-sm italic text-qace-muted">Questions will appear here as the interview progresses.</p>
              ) : (
                questionHistory.slice(-6).map((q, idx) => {
                  const isCurrent = q.index === questionIndex;
                  return (
                    <div
                      key={`q-${q.index}-${idx}`}
                      className={`rounded-xl border px-3 py-2 ${isCurrent
                          ? "border-emerald-300/40 bg-emerald-400/10"
                          : "card-glow border-white/20 bg-black/20"
                        }`}
                    >
                      <div className="flex items-center justify-between">
                        <p className="text-xs text-qace-muted">Q{q.index + 1}</p>
                        <span className={`text-xs ${q.voice === "female" ? "text-pink-300" : "text-blue-300"}`}>
                          {q.voice === "female" ? "♀" : "♂"}
                        </span>
                      </div>
                      <p className="mt-0.5 line-clamp-2 text-xs">{q.text}</p>
                    </div>
                  );
                })
              )}
            </div>
          </section>

          {/* Transcript */}
          {showTranscriptPanel ? (
            <section className="card-glow rounded-2xl border border-white/20 bg-white/5 p-4 shadow-xl shadow-black/20">
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-base font-semibold">Transcript</h2>
                {autoScrollPaused && (
                  <button
                    type="button"
                    onClick={() => setAutoScrollPaused(false)}
                    className="flex items-center gap-1 rounded-lg bg-white/10 px-2 py-1 text-xs hover:bg-white/20"
                  >
                    ↓ Resume
                  </button>
                )}
              </div>
              {latestTranscript && (
                <div className="mb-2 flex gap-4 rounded-lg bg-white/5 px-3 py-1.5 text-xs">
                  <span className="font-mono font-medium text-white/80">{Math.round(latestTranscript.wpm)} WPM</span>
                  <span className={`font-mono ${latestTranscript.filler_count > 2 ? "text-amber-300" : "text-white/45"}`}>
                    {latestTranscript.filler_count} filler{latestTranscript.filler_count !== 1 ? "s" : ""}
                  </span>
                </div>
              )}
              <div
                ref={transcriptScrollRef}
                onScroll={handleTranscriptScroll}
                className="max-h-72 space-y-2 overflow-y-auto pr-1 text-sm"
              >
                {transcripts.length === 0 ? (
                  <p className="italic text-qace-muted">Transcript snippets will appear here during your answer.</p>
                ) : (
                  transcripts.slice(-20).map((t, i) => (
                    <div key={i} className="rounded-lg bg-black/25 p-2.5">
                      <p>{t.text}</p>
                      <p className="mt-0.5 text-[10px] text-white/30">{Math.round(t.wpm)} WPM · {t.filler_count} fillers</p>
                    </div>
                  ))
                )}
              </div>
            </section>
          ) : null}

          {/* System Timeline */}
          <section className="card-glow rounded-2xl border border-white/20 bg-white/5 p-4 shadow-xl shadow-black/20">
            <h2 className="mb-2 text-base font-semibold">System Timeline</h2>
            <div className="max-h-28 space-y-1 overflow-y-auto font-mono text-xs text-qace-muted">
              {statusLog.length === 0 ? <p>No events yet.</p> : statusLog.slice(-6).map((entry, i) => <p key={i}>{entry}</p>)}
            </div>
          </section>
        </aside>
      </div>
    </main>
    {showCodingOverlay ? (
      <div className="fixed inset-0 z-[100] overflow-auto bg-[#071026] p-2">
        <CodingRoundView
          problemId={codingProblemId}
          sessionId={sessionId ?? undefined}
          onDebriefRequest={(scoring) =>
            sendCodingDebrief(scoring as Record<string, unknown>)
          }
          onClose={() => router.replace("/session/live")}
        />
      </div>
    ) : null}
    </>
  );
}

// ── AI Interviewer Avatar ────────────────────────────────────────────────

function AIAvatarCard({ phase, voice }: { phase: string; voice: string }) {
  const isSpeaking = phase === "speaking";
  const isThinking = phase === "thinking" || phase === "evaluating" || phase === "listening";

  return (
    <div className="relative flex h-36 w-full items-center justify-center overflow-hidden">
      {/* Radial backdrop glow */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(56,189,248,0.08)_0%,transparent_70%)]" />

      {/* Sonar rings — speaking only */}
      {isSpeaking && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="avatar-ring-1 absolute h-14 w-14 rounded-full border-2 border-blue-400/65" />
          <div className="avatar-ring-2 absolute h-14 w-14 rounded-full border-2 border-cyan-400/45" />
          <div className="avatar-ring-3 absolute h-14 w-14 rounded-full border border-sky-300/25" />
        </div>
      )}

      {/* Icon frame */}
      <div
        className={[
          "relative z-10 flex h-14 w-14 items-center justify-center rounded-full",
          "border border-blue-400/40 bg-gradient-to-br from-blue-600/20 to-indigo-700/20",
          isSpeaking
            ? "shadow-[0_0_22px_rgba(56,189,248,0.40)]"
            : "shadow-[0_0_12px_rgba(56,189,248,0.12)]",
          isThinking ? "avatar-breathe" : "",
        ].join(" ")}
      >
        {/* Stylised AI head glyph */}
        <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className="h-9 w-9">
          {/* Head shell */}
          <rect x="9" y="10" width="30" height="24" rx="7" fill="rgba(56,189,248,0.10)" stroke="rgba(56,189,248,0.55)" strokeWidth="1.4" />
          {/* Left eye */}
          <rect x="14" y="17" width="7" height="5" rx="2" fill="rgba(56,189,248,0.70)" />
          {/* Right eye */}
          <rect x="27" y="17" width="7" height="5" rx="2" fill="rgba(56,189,248,0.70)" />
          {/* Mouth */}
          <rect x="16" y="27" width="16" height="2.5" rx="1.25" fill="rgba(34,211,238,0.50)" />
          {/* Antenna stem */}
          <line x1="24" y1="10" x2="24" y2="5" stroke="rgba(56,189,248,0.45)" strokeWidth="1.5" strokeLinecap="round" />
          {/* Antenna tip */}
          <circle cx="24" cy="4" r="1.8" fill="rgba(56,189,248,0.65)" />
          {/* Left ear port */}
          <rect x="6" y="17" width="3" height="8" rx="1.5" fill="rgba(56,189,248,0.20)" stroke="rgba(56,189,248,0.35)" strokeWidth="1" />
          {/* Right ear port */}
          <rect x="39" y="17" width="3" height="8" rx="1.5" fill="rgba(56,189,248,0.20)" stroke="rgba(56,189,248,0.35)" strokeWidth="1" />
          {/* Neck */}
          <rect x="20" y="34" width="8" height="4" rx="2" fill="rgba(56,189,248,0.18)" stroke="rgba(56,189,248,0.30)" strokeWidth="1" />
        </svg>
      </div>

      {/* Mic badge — only when speaking */}
      {isSpeaking && (
        <div className="absolute bottom-3 right-[calc(50%-34px)] z-20 flex h-5 w-5 items-center justify-center rounded-full bg-blue-500 shadow-[0_0_8px_rgba(56,189,248,0.6)]">
          <svg viewBox="0 0 16 16" fill="currentColor" className="h-3 w-3 text-white">
            <path d="M8 1a2 2 0 0 0-2 2v4a2 2 0 1 0 4 0V3a2 2 0 0 0-2-2zm0 10a4 4 0 0 1-4-4H2a6 6 0 0 0 5 5.92V15H5v1h6v-1H9v-2.08A6 6 0 0 0 14 7h-2a4 4 0 0 1-4 4z" />
          </svg>
        </div>
      )}

      {/* Thinking dots */}
      {isThinking && (
        <div className="absolute bottom-3 flex gap-1">
          {([0, 0.25, 0.5] as number[]).map((delay) => (
            <div
              key={delay}
              className="h-1.5 w-1.5 rounded-full bg-cyan-400/60"
              style={{ animation: `avatarBreathe 1.2s ease-in-out ${delay}s infinite` }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Score helpers ─────────────────────────────────────────────────────────

function getScoreBand(v: number): { label: string; color: string; bar: string } {
  if (v >= 90) return { label: "Excellent",  color: "text-sky-300",     bar: "from-sky-500 to-sky-400" };
  if (v >= 75) return { label: "Good",       color: "text-emerald-300", bar: "from-emerald-500 to-emerald-400" };
  if (v >= 60) return { label: "Developing", color: "text-amber-300",   bar: "from-amber-500 to-amber-400" };
  return              { label: "Needs Work", color: "text-red-300",     bar: "from-red-500 to-red-400" };
}

function makeVerdict(
  label: string,
  value: number,
  perception: PerceptionEvent | null,
  latest: TranscriptEvent | null,
): string {
  if (label === "Content") {
    if (value >= 90) return "Strong technical depth and clear structure.";
    if (value >= 75) return "Good coverage — a concrete example would strengthen the answer.";
    return "Focus on structuring responses: situation → approach → result.";
  }
  if (label === "Delivery") {
    if (latest) {
      const wpm = Math.round(latest.wpm);
      const f = latest.filler_count;
      return `${wpm} WPM · ${f} filler word${f !== 1 ? "s" : ""} detected.`;
    }
    if (value >= 80) return "Clear, well-paced delivery.";
    return "Work on reducing filler words and steadying pace.";
  }
  if (label === "Composure") {
    if (perception) {
      const vocal = perception.vocal_emotion.toLowerCase();
      const face  = perception.face_emotion.toLowerCase();
      return `Voice ${vocal}, face ${face} — ${value >= 75 ? "projecting composure" : "some tension detected"}.`;
    }
    if (value >= 80) return "Composed and steady throughout.";
    return "Some hesitation or tension detected.";
  }
  return "";
}

function RichScoreRow({ label, value, verdict }: { label: string; value: number; verdict: string }) {
  const safeValue = Math.max(0, Math.min(value, 100));
  const band = getScoreBand(safeValue);
  const criteria = SCORE_CRITERIA[label] ?? [];
  return (
    <div className="group relative space-y-1.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <span className="text-qace-muted">{label}</span>
          <span className="cursor-help text-[10px] text-white/25">ⓘ</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-semibold ${band.color}`}>{band.label}</span>
          <span className="text-xs text-white/35">{safeValue.toFixed(0)}</span>
        </div>
      </div>
      {/* Hover tooltip */}
      <div className="pointer-events-none absolute left-0 top-7 z-20 hidden w-52 rounded-xl border border-white/10 bg-[#0d1425]/95 p-3 shadow-xl group-hover:block">
        <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-qace-muted">Measuring</p>
        <ul className="space-y-0.5">
          {criteria.map((c) => (
            <li key={c} className="text-xs text-white/65">· {c}</li>
          ))}
        </ul>
      </div>
      <div className="h-2 rounded-full bg-white/10">
        <div
          className={`h-2 rounded-full bg-gradient-to-r ${band.bar} transition-[width] duration-500`}
          style={{ width: `${safeValue}%` }}
        />
      </div>
      {verdict && <p className="text-[11px] italic text-white/40">{verdict}</p>}
    </div>
  );
}

// ── Emotion helpers ────────────────────────────────────────────────────────

function Sparkline({ values, color }: { values: number[]; color: string }) {
  if (values.length < 2) return <div className="h-3 w-[50px]" />;
  const W = 50, H = 12;
  const pts = values
    .map((v, i) => {
      const x = ((i / (values.length - 1)) * W).toFixed(1);
      const y = (H - (Math.max(0, Math.min(v, 100)) / 100) * H).toFixed(1);
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg width={W} height={H} className="overflow-visible opacity-60">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function AnimatedEmotionBadge({ label, emotion, history }: { label: string; emotion: string; history: number[] }) {
  const key = emotion.toLowerCase();
  const colors = EMOTION_COLORS[key] ?? EMOTION_DEFAULT_COLORS;
  const prevRef = useRef<string>("");
  const [flashing, setFlashing] = useState(false);

  useEffect(() => {
    if (prevRef.current && prevRef.current !== key) {
      setFlashing(true);
      const t = setTimeout(() => setFlashing(false), 700);
      return () => clearTimeout(t);
    }
    prevRef.current = key;
  }, [key]);

  return (
    <div className="flex items-center justify-between">
      <div
        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-all duration-300 ${colors.bg} ${colors.text} ${
          flashing ? `ring-2 ${colors.ring} ring-offset-1 ring-offset-[#0d152d]` : ""
        }`}
      >
        <span className="text-white/45">{label}:</span>
        <span className="capitalize">{emotion}</span>
      </div>
      <Sparkline values={history} color={colors.dot} />
    </div>
  );
}
