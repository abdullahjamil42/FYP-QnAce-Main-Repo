"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useDataChannel } from "@/hooks/useDataChannel";
import { useWebRTC } from "@/hooks/useWebRTC";
import VideoCanvas from "@/components/VideoCanvas";
import CodingRoundView from "@/components/coding/CodingRoundView";
import { loadSetupConfig, persistSession } from "@/lib/interview-session-store";
import { jobRoles } from "@/lib/mock-data";

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

  const isConnected = state === "connected";
  const isConnecting = state === "connecting";

  const avatarVideoRef = useRef<HTMLVideoElement>(null);
  const ttsAudioRef = useRef<HTMLAudioElement>(null);

  const setup = loadSetupConfig();
  const roleName = jobRoles.find((r) => r.id === setup.jobRole)?.title ?? "Interview";

  // Phase label (no countdown needed)
  useEffect(() => {
    // No timer — phases are unlimited
  }, [currentPhase]);

  useEffect(() => {
    if (avatarVideoRef.current && remoteVideoStream) {
      avatarVideoRef.current.srcObject = remoteVideoStream;
    }
  }, [remoteVideoStream]);

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

  const phaseLabel = currentPhase?.phase ?? "idle";
  const isThinking = phaseLabel === "thinking";
  const isAnswering = phaseLabel === "answering";
  const isComplete = phaseLabel === "complete";
  const questionIndex = currentQuestion?.index ?? -1;
  const totalQuestions = currentQuestion?.total ?? 0;
  const currentVoice = currentQuestion?.voice ?? "male";

  const codingProblemId = sp.get("problemId") || "";
  const showCodingOverlay =
    sp.get("coding") === "1" &&
    codingProblemId.length > 0 &&
    Boolean(sessionId);

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

            {/* Avatar PiP */}
            <div className="card-glow absolute right-6 top-6 z-10 w-52 overflow-hidden rounded-2xl border border-white/20 bg-black/30 backdrop-blur-sm">
              {remoteVideoStream ? (
                <video ref={avatarVideoRef} autoPlay playsInline muted className="h-32 w-full object-cover" />
              ) : (
                <div className="flex h-32 items-center justify-center text-4xl">
                  {currentVoice === "female" ? "👩‍💼" : "👨‍💼"}
                </div>
              )}
              <div className="flex items-center justify-between px-3 py-2 text-xs text-qace-muted">
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
                <ScoreRow label="Content" value={scores.content} />
                <ScoreRow label="Delivery" value={scores.delivery} />
                <ScoreRow label="Composure" value={scores.composure} />
                <div className="card-glow rounded-xl border border-white/20 bg-black/20 px-3 py-2 text-center">
                  <div className="text-3xl font-semibold text-qace-accent">{scores.final.toFixed(1)}</div>
                  <div className="text-xs text-qace-muted">Overall Score</div>
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
              <div className="flex flex-wrap gap-2">
                <EmotionBadge label="Voice" emotion={perception.vocal_emotion} />
                <EmotionBadge label="Face" emotion={perception.face_emotion} />
                <EmotionBadge label="Text" emotion={perception.text_quality_label} />
              </div>
            </section>
          )}

          {/* Question Progress */}
          <section className="card-glow rounded-2xl border border-white/20 bg-white/5 p-4 shadow-xl shadow-black/20">
            <h2 className="mb-3 text-base font-semibold">Question Progress</h2>
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
              <h2 className="mb-2 text-base font-semibold">Transcript</h2>
              <div className="max-h-44 space-y-2 overflow-y-auto pr-1 text-sm">
                {transcripts.length === 0 ? (
                  <p className="italic text-qace-muted">Transcript snippets will appear here during your answer.</p>
                ) : (
                  transcripts.slice(-12).map((t, i) => (
                    <div key={i} className="rounded-lg bg-black/25 p-2.5">
                      <p>{t.text}</p>
                      <p className="mt-1 text-xs text-qace-muted">{t.wpm} WPM · {t.filler_count} fillers</p>
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

function ScoreRow({ label, value }: { label: string; value: number }) {
  const safeValue = Math.max(0, Math.min(value, 100));
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-qace-muted">{label}</span>
        <span className="font-semibold">{safeValue.toFixed(1)}</span>
      </div>
      <div className="h-2 rounded-full bg-white/10">
        <div className="h-2 rounded-full bg-gradient-to-r from-qace-accent to-qace-primary" style={{ width: `${safeValue}%` }} />
      </div>
    </div>
  );
}

const EMOTION_COLORS: Record<string, string> = {
  confident: "bg-emerald-500/20 text-emerald-200",
  composed: "bg-emerald-500/20 text-emerald-200",
  engaged: "bg-blue-500/20 text-blue-200",
  happy: "bg-yellow-500/20 text-yellow-200",
  positive: "bg-emerald-500/20 text-emerald-200",
  neutral: "bg-slate-500/20 text-slate-200",
  nervous: "bg-amber-500/20 text-amber-200",
  anxious: "bg-amber-500/20 text-amber-200",
  stressed: "bg-red-500/20 text-red-200",
  good: "bg-emerald-500/20 text-emerald-200",
  average: "bg-amber-500/20 text-amber-200",
  poor: "bg-red-500/20 text-red-200",
};

function EmotionBadge({ label, emotion }: { label: string; emotion: string }) {
  const color = EMOTION_COLORS[emotion.toLowerCase()] ?? "bg-slate-500/20 text-slate-200";
  return (
    <div className={`rounded-full px-3 py-1.5 text-xs font-medium ${color}`}>
      <span className="text-white/60">{label}:</span>{" "}
      <span className="capitalize">{emotion}</span>
    </div>
  );
}
