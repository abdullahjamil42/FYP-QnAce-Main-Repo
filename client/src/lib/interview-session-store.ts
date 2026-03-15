import type { PerceptionEvent, ScoresEvent, TranscriptEvent } from "@/hooks/useDataChannel";
import { getSupabaseClient } from "@/lib/supabase";

const LOCAL_KEY = "qace_sessions_v1";
const LOCAL_SETUP_KEY = "qace_setup_v1";
const LOCAL_LAST_SUMMARY_KEY = "qace_last_summary_id";

export type SetupConfig = {
  mode: string;
  difficulty: string;
  durationMinutes: number;
};

export type SessionRecord = {
  id: string;
  user_id: string | null;
  mode: string;
  difficulty: string;
  duration_minutes: number;
  status: "completed" | "aborted";
  started_at: string;
  ended_at: string;
  final_score: number;
  content_score: number;
  delivery_score: number;
  composure_score: number;
  transcript_events: TranscriptEvent[];
  latest_perception: PerceptionEvent | null;
  webrtc_session_id: string | null;
  created_at: string;
};

export type SessionDraft = {
  mode: string;
  difficulty: string;
  durationMinutes: number;
  startedAt: string;
  endedAt: string;
  status: "completed" | "aborted";
  scores: ScoresEvent | null;
  transcripts: TranscriptEvent[];
  perception: PerceptionEvent | null;
  webrtcSessionId?: string | null;
};

function getLocalSessions(): SessionRecord[] {
  if (typeof window === "undefined") {
    return [];
  }
  const raw = window.localStorage.getItem(LOCAL_KEY);
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw) as SessionRecord[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function setLocalSessions(records: SessionRecord[]) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(LOCAL_KEY, JSON.stringify(records.slice(0, 100)));
}

function computeSessionRecord(draft: SessionDraft, userId: string | null): SessionRecord {
  const now = new Date().toISOString();
  return {
    id: typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}`,
    user_id: userId,
    mode: draft.mode,
    difficulty: draft.difficulty,
    duration_minutes: draft.durationMinutes,
    status: draft.status,
    started_at: draft.startedAt,
    ended_at: draft.endedAt,
    final_score: draft.scores?.final ?? 0,
    content_score: draft.scores?.content ?? 0,
    delivery_score: draft.scores?.delivery ?? 0,
    composure_score: draft.scores?.composure ?? 0,
    transcript_events: draft.transcripts,
    latest_perception: draft.perception,
    webrtc_session_id: draft.webrtcSessionId ?? null,
    created_at: now,
  };
}

async function getSignedInUserId(): Promise<string | null> {
  const client = getSupabaseClient();
  if (!client) {
    return null;
  }
  const { data } = await client.auth.getUser();
  return data.user?.id ?? null;
}

export function saveSetupConfig(config: SetupConfig) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(LOCAL_SETUP_KEY, JSON.stringify(config));
}

export function loadSetupConfig(): SetupConfig {
  if (typeof window === "undefined") {
    return {
      mode: "technical",
      difficulty: "standard",
      durationMinutes: 20,
    };
  }

  const raw = window.localStorage.getItem(LOCAL_SETUP_KEY);
  if (!raw) {
    return {
      mode: "technical",
      difficulty: "standard",
      durationMinutes: 20,
    };
  }

  try {
    const parsed = JSON.parse(raw) as SetupConfig;
    return {
      mode: parsed.mode || "technical",
      difficulty: parsed.difficulty || "standard",
      durationMinutes: Number(parsed.durationMinutes) || 20,
    };
  } catch {
    return {
      mode: "technical",
      difficulty: "standard",
      durationMinutes: 20,
    };
  }
}

export async function persistSession(draft: SessionDraft): Promise<SessionRecord> {
  const userId = await getSignedInUserId();
  const localRecord = computeSessionRecord(draft, userId);

  const client = getSupabaseClient();
  if (client && userId) {
    const payload = {
      user_id: userId,
      mode: localRecord.mode,
      difficulty: localRecord.difficulty,
      duration_minutes: localRecord.duration_minutes,
      status: localRecord.status,
      started_at: localRecord.started_at,
      ended_at: localRecord.ended_at,
      final_score: localRecord.final_score,
      content_score: localRecord.content_score,
      delivery_score: localRecord.delivery_score,
      composure_score: localRecord.composure_score,
      transcript_events: localRecord.transcript_events,
      latest_perception: localRecord.latest_perception,
      webrtc_session_id: localRecord.webrtc_session_id,
    };

    const sessionsTable = client.from("interview_sessions" as any) as any;
    const { data, error } = await sessionsTable
      .insert(payload)
      .select("*")
      .single();

    if (!error && data) {
      const merged: SessionRecord = {
        ...localRecord,
        ...(data as Record<string, unknown>),
      };
      const sessions = [merged, ...getLocalSessions()];
      setLocalSessions(sessions);
      if (typeof window !== "undefined") {
        window.localStorage.setItem(LOCAL_LAST_SUMMARY_KEY, merged.id);
      }
      return merged;
    }
  }

  const sessions = [localRecord, ...getLocalSessions()];
  setLocalSessions(sessions);
  if (typeof window !== "undefined") {
    window.localStorage.setItem(LOCAL_LAST_SUMMARY_KEY, localRecord.id);
  }
  return localRecord;
}

export async function listSessions(): Promise<SessionRecord[]> {
  const local = getLocalSessions();
  const userId = await getSignedInUserId();
  const client = getSupabaseClient();

  if (!client || !userId) {
    return local;
  }

  const sessionsTable = client.from("interview_sessions" as any) as any;
  const { data, error } = await sessionsTable
    .select("*")
    .order("created_at", { ascending: false })
    .limit(100);

  if (error || !data) {
    return local;
  }

  const merged = data as SessionRecord[];
  setLocalSessions(merged);
  return merged;
}

export async function getSessionById(id: string): Promise<SessionRecord | null> {
  const localMatch = getLocalSessions().find((entry) => entry.id === id);
  const client = getSupabaseClient();
  const userId = await getSignedInUserId();

  if (!client || !userId) {
    return localMatch ?? null;
  }

  const sessionsTable = client.from("interview_sessions" as any) as any;
  const { data, error } = await sessionsTable
    .select("*")
    .eq("id", id)
    .maybeSingle();

  if (error || !data) {
    return localMatch ?? null;
  }

  return data as SessionRecord;
}

export async function getLatestSession(): Promise<SessionRecord | null> {
  const local = getLocalSessions()[0] ?? null;
  const client = getSupabaseClient();
  const userId = await getSignedInUserId();

  if (!client || !userId) {
    return local;
  }

  const sessionsTable = client.from("interview_sessions" as any) as any;
  const { data, error } = await sessionsTable
    .select("*")
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (error || !data) {
    return local;
  }

  return data as SessionRecord;
}

export function getLastSummaryId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(LOCAL_LAST_SUMMARY_KEY);
}
