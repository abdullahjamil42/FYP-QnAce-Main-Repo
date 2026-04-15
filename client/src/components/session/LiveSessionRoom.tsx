"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useDataChannel } from "@/hooks/useDataChannel";
import { useWebRTC } from "@/hooks/useWebRTC";
import VideoCanvas from "@/components/VideoCanvas";
import { loadSetupConfig, persistSession } from "@/lib/interview-session-store";
import InterviewerAvatar, { InterviewerAvatarRef } from "@/components/InterviewerAvatar";

export default function LiveSessionRoom() {
  const router = useRouter();
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
    micGated,
    toggleMic,
    toggleCam,
    applyMicGate,
    start,
    stop,
    addVideoTrack,
  } = useWebRTC();
  const {
    transcripts,
    scores,
    perception,
    statusLog,
    micGated: serverMicGated,
    stage,
    timeWarning,
    sessionEndedReason,
    silencePrompt,
    avatarState,
    clearTranscripts,
    sendAUTelemetry,
  } = useDataChannel(dataChannel, auChannel);
  const startedAtRef = useRef<string | null>(null);
  const isSavingRef = useRef(false);
  const [showTranscriptPanel, setShowTranscriptPanel] = useState(true);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const avatarRef = useRef<InterviewerAvatarRef>(null);

  const formatTime = (totalSeconds: number) => {
    const m = Math.floor(totalSeconds / 60);
    const s = totalSeconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  const isConnected = state === "connected";
  const isConnecting = state === "connecting";

  const avatarVideoRef = useRef<HTMLVideoElement>(null);
  const ttsAudioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    if (avatarVideoRef.current && remoteVideoStream) {
      avatarVideoRef.current.srcObject = remoteVideoStream;
    }
  }, [remoteVideoStream]);

  useEffect(() => {
    const audioEl = ttsAudioRef.current;
    if (!audioEl) {
      return;
    }

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

  // Handle Avatar Lip Sync Connection
  useEffect(() => {
    if (remoteAudioStream && avatarRef.current) {
      avatarRef.current.speak(remoteAudioStream);
    } else if (!remoteAudioStream && avatarRef.current) {
      avatarRef.current.stopSpeaking();
    }
  }, [remoteAudioStream]);

  const handleFaceCropStream = useCallback(
    (stream: MediaStream) => {
      addVideoTrack(stream);
    },
    [addVideoTrack]
  );

  useEffect(() => {
    applyMicGate(serverMicGated);
  }, [serverMicGated, applyMicGate]);

  useEffect(() => {
    if (state === "connected" && !startedAtRef.current) {
      startedAtRef.current = new Date().toISOString();
    }
  }, [state]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (state === "connected" && startedAtRef.current) {
      interval = setInterval(() => {
        const start = new Date(startedAtRef.current!).getTime();
        setElapsedSeconds(Math.floor((Date.now() - start) / 1000));
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [state]);



  const handleStart = useCallback(() => {
    clearTranscripts();
    if (!startedAtRef.current) {
      startedAtRef.current = new Date().toISOString();
    }
    const setup = loadSetupConfig();
    void start(setup.durationMinutes, setup.stressLevel, setup.cvSessionId ?? "");
  }, [clearTranscripts, start]);

  const handleDropCall = useCallback(() => {
    stop();
    clearTranscripts();
    startedAtRef.current = null;
  }, [clearTranscripts, stop]);

  const handleStopAndSave = useCallback(async () => {
    if (isSavingRef.current) {
      return;
    }
    isSavingRef.current = true;

    const setup = loadSetupConfig();
    const startTime = startedAtRef.current ?? new Date().toISOString();
    const endTime = new Date().toISOString();

    try {
      const saved = await persistSession({
        mode: setup.mode,
        difficulty: setup.difficulty,
        durationMinutes: setup.durationMinutes,
        startedAt: startTime,
        endedAt: endTime,
        status: "completed",
        scores,
        transcripts,
        perception,
        webrtcSessionId: sessionId,
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
  }, [perception, router, scores, sessionId, stop, transcripts]);

  useEffect(() => {
    if (sessionEndedReason && state === "connected" && !isSavingRef.current && !isTransitioning) {
      setIsTransitioning(true);
      setTimeout(() => {
        void handleStopAndSave();
      }, 3000);
    }
  }, [sessionEndedReason, state, handleStopAndSave, isTransitioning]);

  if (isTransitioning) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-[#0b1225] via-[#0d152d] to-[#091024] text-qace-text">
        <div className="card-glow flex h-32 w-32 items-center justify-center rounded-3xl border border-white/20 bg-white/5 shadow-2xl animate-pulse">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent" />
        </div>
        <h1 className="mt-8 text-2xl font-semibold tracking-wide text-white">Saving Interview Data...</h1>
        <p className="mt-2 text-qace-muted">Analyzing your performance across all dimensions.</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-black p-4 text-qace-text lg:p-6 selection:bg-[var(--accent-hover)] selection:text-white">
      <div className="apple-gradient-bg" />
      <header className="apple-glass mb-6 flex flex-wrap items-center justify-between gap-3 rounded-[2rem] px-6 py-4">
        <div>
          <p className="text-[10px] uppercase tracking-widest text-[var(--muted)] font-semibold mb-1">Live Interview Room</p>
          <h1 className="text-xl font-bold tracking-tight text-white">Frontend Developer Mock Interview</h1>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="rounded-full bg-black/30 px-2.5 py-1 text-qace-muted">AI Interview Mode</span>
          <span
            className={`rounded-full px-2.5 py-1 font-medium ${isConnected
              ? "bg-emerald-500/25 text-emerald-200"
              : isConnecting
                ? "bg-amber-500/25 text-amber-100"
                : "bg-slate-500/25 text-slate-200"
              }`}
          >
            {state}
          </span>
          {sessionId ? <span className="rounded-full bg-black/30 px-2.5 py-1 text-qace-muted">ID {sessionId.slice(0, 8)}</span> : null}
        </div>
      </header>

      {error ? (
        <div className="mb-4 rounded-xl border border-red-400/30 bg-red-500/15 p-3 text-sm text-red-100">
          <strong>Error:</strong> {error}
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-12">
        <section className="lg:col-span-8">
          <div className="apple-glass relative overflow-hidden rounded-[2.5rem] p-4 shadow-2xl">
            <div className="absolute left-8 top-8 z-10 flex items-center gap-2 rounded-full bg-black/50 px-3 py-1.5 text-[11px] font-semibold tracking-wide backdrop-blur-md">
              <span className={`h-2 w-2 rounded-full ${isConnected ? "bg-red-400 animate-pulse" : "bg-slate-400"}`} />
              <span>{isConnected ? "Live Recording" : "Not Connected"}</span>
            </div>

            {timeWarning !== null && timeWarning <= 5 && (
              <div className="absolute right-4 top-4 z-10 flex items-center gap-2 rounded-full bg-amber-500/90 px-3 py-1 text-xs font-semibold text-white shadow-lg shadow-amber-500/50 animate-pulse">
                <span>⏱️ {timeWarning} min left</span>
              </div>
            )}
            
            <audio ref={ttsAudioRef} autoPlay playsInline className="hidden" />

            {webcamStream ? (
              <VideoCanvas
                videoStream={webcamStream}
                onFaceCropStream={handleFaceCropStream}
                onAUTelemetry={sendAUTelemetry}
                showOverlay={true}
                showStats={false}
                containerClassName="w-full"
                videoClassName="h-[460px] w-full rounded-[2rem] object-cover"
              />
            ) : (
              <div className="flex h-[460px] w-full items-center justify-center rounded-[2rem] bg-zinc-900 text-6xl">📷</div>
            )}

            <div className={`absolute right-8 top-8 z-20 w-[240px] h-[320px] overflow-hidden rounded-[1.5rem] bg-black/40 backdrop-blur-2xl shadow-2xl border transition-all duration-300 ${avatarState === "AVATAR_INTERRUPT" ? "border-red-500/50 shadow-[0_0_30px_rgba(239,68,68,0.3)] scale-105" : avatarState === "AVATAR_COLD" ? "border-blue-400/30" : "border-white/10"}`}>
              <InterviewerAvatar 
                ref={avatarRef}
                avatarState={avatarState}
                containerClassName="w-full h-full"
              />
              <div className="flex items-center justify-between px-4 py-2 text-[10px] text-[var(--muted)] font-semibold uppercase tracking-wider bg-black/50 absolute bottom-0 left-0 right-0 backdrop-blur-lg">
                <span>AI Interviewer</span>
                <span className={serverMicGated ? "text-blue-400 animate-pulse" : remoteAudioStream ? "text-green-400" : ""}>
                  {serverMicGated ? "Thinking..." : remoteAudioStream ? "Connected" : "Ready"}
                </span>
              </div>
            </div>

            {silencePrompt && isConnected && (
              <div className="absolute left-1/2 top-8 z-10 -translate-x-1/2 rounded-full border border-blue-400/30 bg-blue-500/20 px-6 py-2 text-center backdrop-blur-xl shadow-2xl animate-fade-up">
                <p className="font-semibold text-blue-100 text-sm tracking-wide">{silencePrompt}</p>
              </div>
            )}

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
                disabled={!isConnected || micGated}
                className={`rounded-full px-5 py-2 text-sm font-semibold text-white transition disabled:opacity-40 ${micGated
                  ? "bg-violet-600 animate-pulse"
                  : isMicEnabled
                    ? "bg-slate-700 hover:bg-slate-600"
                    : "bg-amber-600 hover:bg-amber-500"
                  }`}
              >
                {micGated ? "Processing…" : isMicEnabled ? "Mic On" : "Mic Off"}
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
                End and Save
              </button>
            </div>
          </div>
        </section>

        <aside className="space-y-4 lg:col-span-4">
          <section className="card-glow rounded-2xl border border-white/20 bg-white/5 p-4 shadow-xl shadow-black/20">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold">Session Progress</h2>
              <span className="rounded-full bg-qace-primary/20 px-2 py-1 text-xs text-indigo-200">
                {stage ? stage.replace("_", " ") : "CONNECTING"}
              </span>
            </div>
            
            <div className="card-glow mt-4 flex items-center justify-center rounded-xl border border-white/20 bg-black/20 px-3 py-4">
              <div className="text-center">
                <div className="text-4xl font-mono tracking-wider font-semibold text-qace-accent">
                  {formatTime(elapsedSeconds)}
                </div>
                <div className="mt-1 text-xs text-qace-muted uppercase tracking-wider">
                  Time Elapsed
                </div>
              </div>
            </div>
          </section>

          <section className="card-glow rounded-2xl border border-white/20 bg-white/5 p-4 shadow-xl shadow-black/20">
            <h2 className="mb-3 text-base font-semibold">Question Queue</h2>
            <div className="space-y-2 text-sm">
              {["Tell me about yourself.", "How would you optimize a React app?", "How do you structure reusable components?", "How do you handle API failure states?"].map((question, idx) => (
                <div key={question} className={`rounded-xl border px-3 py-2 ${idx === 0 ? "border-emerald-300/40 bg-emerald-400/10" : "card-glow border-white/20 bg-black/20"}`}>
                  <p className="text-xs text-qace-muted">Q{idx + 1}</p>
                  <p>{question}</p>
                </div>
              ))}
            </div>
          </section>

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
              {perception ? (
                <div className="card-glow mt-3 rounded-xl border border-white/20 bg-black/25 p-3 text-xs text-qace-muted">
                  <p>Emotion: <span className="capitalize text-white">{perception.vocal_emotion}</span></p>
                  <p>Face: <span className="capitalize text-white">{perception.face_emotion}</span></p>
                  <p>Text: <span className="capitalize text-white">{perception.text_quality_label}</span></p>
                </div>
              ) : null}
            </section>
          ) : null}

          <section className="card-glow rounded-2xl border border-white/20 bg-white/5 p-4 shadow-xl shadow-black/20">
            <h2 className="mb-2 text-base font-semibold">System Timeline</h2>
            <div className="max-h-28 space-y-1 overflow-y-auto font-mono text-xs text-qace-muted">
              {statusLog.length === 0 ? <p>No events yet.</p> : statusLog.slice(-6).map((entry, i) => <p key={i}>{entry}</p>)}
            </div>
          </section>
        </aside>
      </div>
    </main>
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

