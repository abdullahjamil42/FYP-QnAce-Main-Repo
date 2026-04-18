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
 *  - phase: { phase, duration_s }
 *  - question: { text, index, total, question_type, voice }
 *  - interview_end: { total_questions, answered, skipped }
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

export interface PhaseEvent {
  phase:
    | "idle"
    | "intro"
    | "speaking"
    | "thinking"
    | "answering"
    | "transition"
    | "complete"
    | "coding";
  duration_s: number;
}

export interface QuestionEvent {
  text: string;
  index: number;
  total: number;
  question_type: string;
  voice: "male" | "female";
}

export interface PerQuestionScore {
  index: number;
  question: string;
  score: number;
  content: number;
  delivery: number;
  composure: number;
  skipped: boolean;
}

export interface InterviewEndEvent {
  total_questions: number;
  answered: number;
  skipped: number;
  per_question_scores: PerQuestionScore[];
  avg_total_score: number;
}

export interface InterviewerFeedbackEvent {
  text: string;
  mode: string;
}

export type ChannelEvent =
  | ({ type: "transcript" } & TranscriptEvent)
  | ({ type: "scores" } & ScoresEvent)
  | ({ type: "perception" } & PerceptionEvent)
  | ({ type: "status" } & StatusEvent)
  | ({ type: "phase" } & PhaseEvent)
  | ({ type: "question" } & QuestionEvent)
  | ({ type: "interviewer_feedback" } & InterviewerFeedbackEvent)
  | ({ type: "interview_end" } & InterviewEndEvent);

export function useDataChannel(
  dataChannel: RTCDataChannel | null,
  auChannel?: RTCDataChannel | null
) {
  const [transcripts, setTranscripts] = useState<TranscriptEvent[]>([]);
  const [latestTranscript, setLatestTranscript] =
    useState<TranscriptEvent | null>(null);
  const [scores, setScores] = useState<ScoresEvent | null>(null);
  const [perception, setPerception] = useState<PerceptionEvent | null>(null);
  const [statusLog, setStatusLog] = useState<string[]>([]);
  const [currentPhase, setCurrentPhase] = useState<PhaseEvent | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<QuestionEvent | null>(null);
  const [questionHistory, setQuestionHistory] = useState<QuestionEvent[]>([]);
  const [interviewEnd, setInterviewEnd] = useState<InterviewEndEvent | null>(null);

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
            setScores({
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
              ...prev.slice(-19),
              `[${new Date().toLocaleTimeString()}] ${parsed.message}`,
            ]);
            break;
          case "phase":
            setCurrentPhase({
              phase: parsed.phase,
              duration_s: parsed.duration_s,
            });
            break;
          case "question": {
            const q: QuestionEvent = {
              text: parsed.text,
              index: parsed.index,
              total: parsed.total,
              question_type: parsed.question_type,
              voice: parsed.voice,
            };
            setCurrentQuestion(q);
            if (parsed.index >= 0) {
              setQuestionHistory((prev) => [...prev, q]);
            }
            break;
          }
          case "interviewer_feedback": {
            // Follow-up probe from the interviewer — update the displayed
            // question so the UI reflects what the user is now being asked,
            // and keep it out of questionHistory (it's a probe, not a new Q).
            setCurrentQuestion((prev) => ({
              text: parsed.text,
              index: prev?.index ?? -3,
              total: prev?.total ?? 0,
              question_type: `follow_up:${parsed.mode}`,
              voice: prev?.voice ?? "male",
            }));
            break;
          }
          case "interview_end":
            setInterviewEnd({
              total_questions: parsed.total_questions,
              answered: parsed.answered,
              skipped: parsed.skipped,
              per_question_scores: (parsed as any).per_question_scores ?? [],
              avg_total_score: (parsed as any).avg_total_score ?? 0,
            });
            break;
        }
      } catch {
        // Non-JSON message — ignore
      }
    };

    dataChannel.addEventListener("message", handler);
    return () => dataChannel.removeEventListener("message", handler);
  }, [dataChannel]);

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

  const sendCommand = useCallback(
    (command: string) => {
      if (dataChannel && dataChannel.readyState === "open") {
        try {
          dataChannel.send(JSON.stringify({ type: command }));
        } catch {
          // Non-critical
        }
      }
    },
    [dataChannel]
  );

  const sendCodingDebrief = useCallback(
    (scoring: Record<string, unknown>) => {
      if (dataChannel && dataChannel.readyState === "open") {
        try {
          dataChannel.send(
            JSON.stringify({
              type: "coding_debrief_request",
              scoring_json: scoring,
            })
          );
        } catch {
          // Non-critical
        }
      }
    },
    [dataChannel]
  );

  const clearTranscripts = useCallback(() => {
    setTranscripts([]);
    setLatestTranscript(null);
  }, []);

  return {
    transcripts,
    latestTranscript,
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
  };
}
