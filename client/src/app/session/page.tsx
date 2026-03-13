"use client";

import { useCallback, useEffect, useRef } from "react";
import { useDataChannel } from "@/hooks/useDataChannel";
import { useWebRTC } from "@/hooks/useWebRTC";
import VideoCanvas from "@/components/VideoCanvas";

export default function SessionPage() {
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
  const {
    transcripts,
    scores,
    perception,
    statusLog,
    sendAUTelemetry,
  } = useDataChannel(dataChannel, auChannel);

  const isConnected = state === "connected";
  const isConnecting = state === "connecting";

  // ── Refs for remote media playback ──
  const avatarVideoRef = useRef<HTMLVideoElement>(null);
  const ttsAudioRef = useRef<HTMLAudioElement>(null);

  // Attach remote avatar video stream
  useEffect(() => {
    if (avatarVideoRef.current && remoteVideoStream) {
      avatarVideoRef.current.srcObject = remoteVideoStream;
    }
  }, [remoteVideoStream]);

  // Attach remote TTS audio stream
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

  // Wire face crop stream to WebRTC video track
  const handleFaceCropStream = useCallback(
    (stream: MediaStream) => {
      addVideoTrack(stream);
    },
    [addVideoTrack]
  );

  return (
    <main className="flex min-h-screen flex-col gap-6 p-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">
          Q&<span className="text-qace-primary">Ace</span>{" "}
          <span className="text-sm font-normal text-qace-muted">Session</span>
        </h1>
        <div className="flex items-center gap-3">
          <span
            className={`h-3 w-3 rounded-full ${
              isConnected
                ? "bg-green-400"
                : isConnecting
                  ? "bg-yellow-400 animate-pulse"
                  : "bg-gray-500"
            }`}
          />
          <span className="text-sm text-qace-muted capitalize">{state}</span>
          {sessionId && (
            <span className="text-xs text-qace-muted/50">{sessionId.slice(0, 8)}</span>
          )}
        </div>
      </header>

      {error && (
        <div className="rounded-lg bg-red-900/40 px-4 py-3 text-sm text-red-300">
          <strong>Error:</strong> {error}
          <br />
          <span className="text-xs text-red-400">
            Make sure the backend is running on port 8000
          </span>
        </div>
      )}

      <div className="grid flex-1 grid-cols-1 gap-6 lg:grid-cols-4">
        {/* ── Column 1: Avatar + Webcam + Controls ── */}
        <div className="flex flex-col items-center gap-4">
          {/* AI Avatar video */}
          <div className="relative h-64 w-64 overflow-hidden rounded-2xl bg-qace-surface shadow-lg">
            {remoteVideoStream ? (
              <video
                ref={avatarVideoRef}
                autoPlay
                playsInline
                muted
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center">
                <span className="text-5xl">🧑‍💼</span>
              </div>
            )}
            {remoteVideoStream && (
              <span className="absolute bottom-1 left-2 text-xs text-white/60">
                AI Interviewer
              </span>
            )}
          </div>

          {/* TTS audio element (hidden) */}
          <audio ref={ttsAudioRef} autoPlay playsInline className="hidden" />

          <div className="text-xs text-qace-muted/70">
            Voice: {remoteAudioStream ? "connected" : "waiting for TTS audio"}
          </div>

          {/* User webcam */}
          {webcamStream ? (
            <VideoCanvas
              videoStream={webcamStream}
              onFaceCropStream={handleFaceCropStream}
              onAUTelemetry={sendAUTelemetry}
              showOverlay={true}
            />
          ) : (
            <div className="flex h-64 w-64 items-center justify-center rounded-2xl bg-qace-surface shadow-lg">
              <span className="text-6xl">🧑‍💼</span>
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={start}
              disabled={isConnected || isConnecting}
              className="rounded-lg bg-qace-primary px-6 py-2 font-semibold text-white
                         transition-all hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {isConnecting ? "Connecting…" : "Start"}
            </button>
            <button
              onClick={stop}
              disabled={!isConnected}
              className="rounded-lg bg-red-600 px-6 py-2 font-semibold text-white
                         transition-all hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Stop
            </button>
          </div>
        </div>

        {/* ── Column 2: Transcript ── */}
        <div className="flex flex-col gap-3 lg:col-span-1">
          <h2 className="text-lg font-semibold text-qace-muted">Transcript</h2>
          <div className="flex flex-1 flex-col gap-2 overflow-y-auto rounded-xl bg-qace-surface p-4 shadow">
            {transcripts.length === 0 ? (
              <p className="text-sm text-qace-muted/60 italic">
                {isConnected ? "Listening… speak to see your transcript" : 'Click "Start" to begin'}
              </p>
            ) : (
              transcripts.map((t, i) => <TranscriptCard key={i} transcript={t} />)
            )}
          </div>
        </div>

        {/* ── Column 3: Scores ── */}
        <div className="flex flex-col gap-4">
          <div className="rounded-xl bg-qace-surface p-4 shadow">
            <h2 className="mb-3 text-lg font-semibold text-qace-muted">Scores</h2>
            {scores ? (
              <div className="flex flex-col gap-3 text-sm">
                <div className="grid grid-cols-2 gap-3">
                  <ScoreItem label="Content" value={scores.content} weight={70} />
                  <ScoreItem label="Delivery" value={scores.delivery} weight={20} />
                  <ScoreItem label="Composure" value={scores.composure} weight={10} />
                  <div className="col-span-2 border-t border-qace-dark pt-2 text-center">
                    <span className="text-2xl font-bold text-qace-accent">{scores.final.toFixed(1)}</span>
                    <span className="text-xs text-qace-muted"> / 100</span>
                  </div>
                </div>
                {scores.utterance_count && scores.utterance_count > 1 && (
                  <div className="border-t border-qace-dark pt-2 text-xs text-qace-muted/70">
                    <div className="font-semibold mb-1">Running Average ({scores.utterance_count} responses)</div>
                    <div className="grid grid-cols-3 gap-1">
                      <span>C: {scores.avg_content?.toFixed(1)}</span>
                      <span>D: {scores.avg_delivery?.toFixed(1)}</span>
                      <span>Co: {scores.avg_composure?.toFixed(1)}</span>
                    </div>
                    <div className="mt-1 font-semibold">Avg: {scores.avg_final?.toFixed(1)}/100</div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-qace-muted/60 italic">
                Scores appear after your first response
              </p>
            )}
          </div>

          <div className="rounded-xl bg-qace-surface p-4 shadow">
            <h2 className="mb-2 text-sm font-semibold text-qace-muted">Status</h2>
            <div className="flex max-h-40 flex-col gap-1 overflow-y-auto font-mono text-xs text-qace-muted/80">
              {statusLog.length === 0 ? (
                <span className="italic">No events yet</span>
              ) : (
                statusLog.map((s, i) => <div key={i}>{s}</div>)
              )}
            </div>
          </div>
        </div>

        {/* ── Column 4: Perception ── */}
        <div className="flex flex-col gap-4">
          <div className="rounded-xl bg-qace-surface p-4 shadow">
            <h2 className="mb-3 text-lg font-semibold text-qace-muted">Perception</h2>
            {perception ? (
              <div className="flex flex-col gap-3 text-sm">
                <PerceptionItem
                  label="Vocal Emotion"
                  value={perception.vocal_emotion}
                  confidence={perception.acoustic_confidence}
                />
                <PerceptionItem
                  label="Face Emotion"
                  value={perception.face_emotion}
                />
                <PerceptionItem
                  label="Text Quality"
                  value={perception.text_quality_label}
                  score={perception.text_quality_score}
                />
                <div className="border-t border-qace-dark pt-2 text-xs text-qace-muted/60">
                  Parallel: {perception.parallel_wall_ms}ms · Total: {perception.total_wall_ms}ms
                </div>
              </div>
            ) : (
              <p className="text-sm text-qace-muted/60 italic">
                Perception data appears during analysis
              </p>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}

function TranscriptCard({
  transcript,
}: {
  transcript: {
    text: string;
    inference_ms: number;
    wpm: number;
    filler_count: number;
  };
}) {
  return (
    <div className="rounded-lg bg-qace-dark/50 px-3 py-2 text-sm">
      <p>{transcript.text}</p>
      <p className="mt-1 text-xs text-qace-muted">
        {transcript.inference_ms}ms · {transcript.wpm} WPM · {transcript.filler_count} fillers
      </p>
    </div>
  );
}

function ScoreItem({
  label,
  value,
  weight,
}: {
  label: string;
  value: number;
  weight: number;
}) {
  return (
    <div>
      <div className="flex justify-between">
        <span>{label}</span>
        <span className="font-mono">{value.toFixed(1)}</span>
      </div>
      <div className="mt-1 h-1.5 rounded-full bg-qace-dark">
        <div
          className="h-full rounded-full bg-qace-primary transition-all"
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
      <span className="text-xs text-qace-muted/50">{weight}% weight</span>
    </div>
  );
}

function PerceptionItem({
  label,
  value,
  confidence,
  score,
}: {
  label: string;
  value: string;
  confidence?: number;
  score?: number;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-qace-muted">{label}</span>
      <div className="flex items-center gap-2">
        <span className="font-semibold capitalize">{value}</span>
        {confidence !== undefined && (
          <span className="text-xs text-qace-muted/60">
            {(confidence * 100).toFixed(0)}%
          </span>
        )}
        {score !== undefined && (
          <span className="text-xs text-qace-muted/60">{score}/100</span>
        )}
      </div>
    </div>
  );
}
