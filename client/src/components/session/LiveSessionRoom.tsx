"use client";

import { useCallback, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useDataChannel } from "@/hooks/useDataChannel";
import { useWebRTC } from "@/hooks/useWebRTC";
import VideoCanvas from "@/components/VideoCanvas";
import { loadSetupConfig, persistSession } from "@/lib/interview-session-store";

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
    start,
    stop,
    addVideoTrack,
  } = useWebRTC();
  const { transcripts, scores, perception, statusLog, sendAUTelemetry } = useDataChannel(dataChannel, auChannel);
  const startedAtRef = useRef<string | null>(null);
  const isSavingRef = useRef(false);

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
    if (!startedAtRef.current) {
      startedAtRef.current = new Date().toISOString();
    }
    void start();
  }, [start]);

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

  return (
    <main className="min-h-screen bg-gradient-to-b from-[#0b1225] via-[#0d152d] to-[#091024] p-4 text-qace-text lg:p-6">
      <header className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/20 bg-white/5 px-4 py-3 shadow-xl shadow-black/20">
        <div>
          <p className="text-xs uppercase tracking-wide text-qace-muted">Q&Ace Live Interview Room</p>
          <h1 className="text-xl font-semibold">Frontend Developer Mock Interview</h1>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="rounded-full bg-black/30 px-2.5 py-1 text-qace-muted">AI Interview Mode</span>
          <span
            className={`rounded-full px-2.5 py-1 font-medium ${
              isConnected
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

      <div className="grid gap-4 lg:grid-cols-12">
        <section className="lg:col-span-8">
          <div className="relative overflow-hidden rounded-3xl border border-white/20 bg-[#12182a] p-3 shadow-2xl shadow-black/35">
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
              <div className="flex h-[420px] w-full items-center justify-center rounded-2xl bg-qace-surface text-6xl">📷</div>
            )}

            <div className="absolute right-6 top-6 z-10 w-52 overflow-hidden rounded-2xl border border-white/20 bg-black/30 backdrop-blur-sm">
              {remoteVideoStream ? (
                <video ref={avatarVideoRef} autoPlay playsInline muted className="h-32 w-full object-cover" />
              ) : (
                <div className="flex h-32 items-center justify-center text-4xl">🧑‍💼</div>
              )}
              <div className="flex items-center justify-between px-3 py-2 text-xs text-qace-muted">
                <span>AI Interviewer</span>
                <span>{remoteAudioStream ? "voice on" : "voice wait"}</span>
              </div>
            </div>

            <div className="mt-3 flex flex-wrap items-center justify-center gap-2 rounded-2xl border border-white/20 bg-black/25 px-3 py-3">
              <button
                onClick={handleStart}
                disabled={isConnected || isConnecting}
                className="rounded-full bg-emerald-500 px-5 py-2 text-sm font-semibold text-white transition hover:bg-emerald-400 disabled:opacity-40"
              >
                {isConnecting ? "Connecting..." : "Join Interview"}
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
          <section className="rounded-2xl border border-white/20 bg-white/5 p-4 shadow-xl shadow-black/20">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold">Interview Intelligence</h2>
              <span className="rounded-full bg-qace-primary/20 px-2 py-1 text-xs text-indigo-200">AI Analysis</span>
            </div>
            {scores ? (
              <div className="space-y-3 text-sm">
                <ScoreRow label="Content" value={scores.content} />
                <ScoreRow label="Delivery" value={scores.delivery} />
                <ScoreRow label="Composure" value={scores.composure} />
                <div className="rounded-xl border border-white/20 bg-black/20 px-3 py-2 text-center">
                  <div className="text-3xl font-semibold text-qace-accent">{scores.final.toFixed(1)}</div>
                  <div className="text-xs text-qace-muted">Overall Score</div>
                </div>
              </div>
            ) : (
              <p className="text-sm italic text-qace-muted">Start speaking to unlock score and coaching metrics.</p>
            )}
          </section>

          <section className="rounded-2xl border border-white/20 bg-white/5 p-4 shadow-xl shadow-black/20">
            <h2 className="mb-3 text-base font-semibold">Question Queue</h2>
            <div className="space-y-2 text-sm">
              {["Tell me about yourself.", "How would you optimize a React app?", "How do you structure reusable components?", "How do you handle API failure states?"].map((question, idx) => (
                <div key={question} className={`rounded-xl border px-3 py-2 ${idx === 0 ? "border-emerald-300/40 bg-emerald-400/10" : "border-white/20 bg-black/20"}`}>
                  <p className="text-xs text-qace-muted">Q{idx + 1}</p>
                  <p>{question}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-2xl border border-white/20 bg-white/5 p-4 shadow-xl shadow-black/20">
            <h2 className="mb-2 text-base font-semibold">Live Notes</h2>
            <div className="max-h-44 space-y-2 overflow-y-auto pr-1 text-sm">
              {transcripts.length === 0 ? (
                <p className="italic text-qace-muted">Transcript snippets will appear here during your answer.</p>
              ) : (
                transcripts.slice(-3).map((t, i) => (
                  <div key={i} className="rounded-lg bg-black/25 p-2.5">
                    <p>{t.text}</p>
                    <p className="mt-1 text-xs text-qace-muted">{t.wpm} WPM · {t.filler_count} fillers</p>
                  </div>
                ))
              )}
            </div>
            {perception ? (
              <div className="mt-3 rounded-xl border border-white/20 bg-black/25 p-3 text-xs text-qace-muted">
                <p>Emotion: <span className="capitalize text-white">{perception.vocal_emotion}</span></p>
                <p>Face: <span className="capitalize text-white">{perception.face_emotion}</span></p>
                <p>Text: <span className="capitalize text-white">{perception.text_quality_label}</span></p>
              </div>
            ) : null}
          </section>

          <section className="rounded-2xl border border-white/20 bg-white/5 p-4 shadow-xl shadow-black/20">
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

