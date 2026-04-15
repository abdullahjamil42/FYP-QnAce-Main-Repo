/**
 * Q&Ace — useDataChannel hook.
 *
 * Subscribes to events from the server DataChannel ('qace-events').
 * Parses JSON messages and dispatches to typed callbacks.
 * Also manages AU telemetry transmission on the 'au-telemetry' channel.
 *
 * Event types:
 *  - transcript: { text, inference_ms, wpm, filler_count }
 *  - scores: { content, delivery, composure, final }
 *  - perception: { vocal_emotion, face_emotion, text_quality_label, ... }
 *  - status: { message }
 */

import { useCallback, useEffect, useState } from "react";

export interface TranscriptEvent {
  text: string;
  inference_ms: number;
  wpm: number;
  filler_count: number;
}

export interface ScoresEvent {
  content: number;
  delivery: number;
  composure: number;
  final: number;
  avg_content?: number;
  avg_delivery?: number;
  avg_composure?: number;
  avg_final?: number;
  utterance_count?: number;
}

export interface PerceptionEvent {
  vocal_emotion: string;
  face_emotion: string;
  text_quality_label: string;
  text_quality_score: number;
  acoustic_confidence: number;
  parallel_wall_ms: number;
  total_wall_ms: number;
}

export interface StatusEvent {
  message: string;
}

export interface MicGateEvent {
  state: "disabled" | "enabled";
  reason: string;
}

export interface StageChangeEvent {
  stage: string;
}

export interface TimeWarningEvent {
  remaining_minutes: number;
}

export interface AvatarStateEvent {
  state: string;
}

export interface SessionEndedEvent {
  reason: string;
}

export interface SilencePromptEvent {
  text: string;
}

export type ChannelEvent =
  | ({ type: "transcript" } & TranscriptEvent)
  | ({ type: "scores" } & ScoresEvent)
  | ({ type: "perception" } & PerceptionEvent)
  | ({ type: "status" } & StatusEvent)
  | ({ type: "mic_gate" } & MicGateEvent)
  | ({ type: "stage_change" } & StageChangeEvent)
  | ({ type: "time_warning" } & TimeWarningEvent)
  | ({ type: "session_ended" } & SessionEndedEvent)
  | ({ type: "silence_prompt" } & SilencePromptEvent)
  | ({ type: "avatar_state" } & AvatarStateEvent);

export function useDataChannel(
  dataChannel: RTCDataChannel | null,
  auChannel?: RTCDataChannel | null
) {
  const [transcripts, setTranscripts] = useState<TranscriptEvent[]>([]);
  const [latestTranscript, setLatestTranscript] =
    useState<TranscriptEvent | null>(null);
  const [currentScores, setCurrentScores] = useState<ScoresEvent | null>(null);
  const [perception, setPerception] = useState<PerceptionEvent | null>(null);
  const [statusLog, setStatusLog] = useState<string[]>([]);
  const [micGated, setMicGated] = useState(false);
  
  // Realism Engine States
  const [stage, setStage] = useState<string | null>(null);
  const [timeWarning, setTimeWarning] = useState<number | null>(null);
  const [sessionEndedReason, setSessionEndedReason] = useState<string | null>(null);
  const [silencePrompt, setSilencePrompt] = useState<string | null>(null);
  const [avatarState, setAvatarState] = useState<string | null>(null);

  // Handle JSON events from server
  useEffect(() => {
    if (!dataChannel) return;

    const handler = (ev: MessageEvent) => {
      try {
        const parsed: ChannelEvent = JSON.parse(ev.data);

        switch (parsed.type) {
          case "transcript": {
            const t: TranscriptEvent = {
              text: parsed.text,
              inference_ms: parsed.inference_ms,
              wpm: parsed.wpm,
              filler_count: parsed.filler_count,
            };
            setLatestTranscript(t);
            setTranscripts((prev) => [...prev, t]);
            break;
          }
          case "scores":
            setCurrentScores({
              content: parsed.content,
              delivery: parsed.delivery,
              composure: parsed.composure,
              final: parsed.final,
              avg_content: (parsed as any).avg_content,
              avg_delivery: (parsed as any).avg_delivery,
              avg_composure: (parsed as any).avg_composure,
              avg_final: (parsed as any).avg_final,
              utterance_count: (parsed as any).utterance_count,
            });
            break;
          case "perception":
            setPerception({
              vocal_emotion: parsed.vocal_emotion,
              face_emotion: parsed.face_emotion,
              text_quality_label: parsed.text_quality_label,
              text_quality_score: parsed.text_quality_score,
              acoustic_confidence: parsed.acoustic_confidence,
              parallel_wall_ms: parsed.parallel_wall_ms,
              total_wall_ms: parsed.total_wall_ms,
            });
            break;
          case "status":
            setStatusLog((prev) => [
              ...prev.slice(-19), // keep last 20
              `[${new Date().toLocaleTimeString()}] ${parsed.message}`,
            ]);
            break;
          case "mic_gate":
            setMicGated(parsed.state === "disabled");
            setStatusLog((prev) => [
              ...prev.slice(-19),
              `[${new Date().toLocaleTimeString()}] System mic gate: ${parsed.state} (${parsed.reason})`,
            ]);
            break;
          case "stage_change":
            setStage(parsed.stage);
            setStatusLog((prev) => [
              ...prev.slice(-19),
              `[${new Date().toLocaleTimeString()}] Stage -> ${parsed.stage}`,
            ]);
            break;
          case "time_warning":
            setTimeWarning(parsed.remaining_minutes);
            break;
          case "session_ended":
            setSessionEndedReason(parsed.reason);
            break;
          case "silence_prompt":
            setSilencePrompt(parsed.text);
            break;
          case "avatar_state":
            setAvatarState(parsed.state);
            setStatusLog((prev) => [
              ...prev.slice(-19),
              `[${new Date().toLocaleTimeString()}] Avatar Event: ${parsed.state}`,
            ]);
            break;
        }
      } catch {
        // Non-JSON message — ignore
      }
    };

    dataChannel.addEventListener("message", handler);
    return () => dataChannel.removeEventListener("message", handler);
  }, [dataChannel]);

  // Send AU telemetry (binary) — called by VideoCanvas at ~10Hz
  const sendAUTelemetry = useCallback(
    (buffer: ArrayBuffer) => {
      if (auChannel && auChannel.readyState === "open") {
        try {
          auChannel.send(buffer);
        } catch {
          // Non-critical — AU telemetry is fire-and-forget
        }
      }
    },
    [auChannel]
  );

  const clearTranscripts = useCallback(() => {
    setTranscripts([]);
    setLatestTranscript(null);
  }, []);

  return {
    transcripts,
    latestTranscript,
    scores: currentScores,
    perception,
    statusLog,
    micGated,
    stage,
    timeWarning,
    sessionEndedReason,
    silencePrompt,
    avatarState,
    clearTranscripts,
    sendAUTelemetry,
  };
}
