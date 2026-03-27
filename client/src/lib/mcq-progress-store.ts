import { getSupabaseClient } from "@/lib/supabase";

const LOCAL_ATTEMPTS_KEY = "qace_mcq_attempts_v1";
const LOCAL_PROGRESS_KEY = "qace_mcq_progress_v1";

export type MCQAttemptAnswer = {
  questionId: string;
  selectedOptionId: string;
  correctOptionId: string;
  isCorrect: boolean;
};

export type MCQAttemptDraft = {
  topicId: string;
  startedAt: string;
  completedAt: string;
  totalQuestions: number;
  correctAnswers: number;
  scorePercent: number;
  answers: MCQAttemptAnswer[];
  feedbackSummary: string;
};

export type MCQAttemptRecord = {
  id: string;
  user_id: string | null;
  topic_id: string;
  started_at: string;
  completed_at: string;
  total_questions: number;
  correct_answers: number;
  score_percent: number;
  answers: MCQAttemptAnswer[];
  feedback_summary: string;
  created_at: string;
};

export type MCQTopicProgress = {
  topic_id: string;
  attempts_count: number;
  best_score: number;
  average_score: number;
  latest_score: number;
  last_attempt_at: string;
};

function generateId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}`;
}

function getLocalAttempts(): MCQAttemptRecord[] {
  if (typeof window === "undefined") {
    return [];
  }
  const raw = window.localStorage.getItem(LOCAL_ATTEMPTS_KEY);
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw) as MCQAttemptRecord[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function setLocalAttempts(items: MCQAttemptRecord[]) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(LOCAL_ATTEMPTS_KEY, JSON.stringify(items.slice(0, 200)));
}

function getLocalProgress(): MCQTopicProgress[] {
  if (typeof window === "undefined") {
    return [];
  }
  const raw = window.localStorage.getItem(LOCAL_PROGRESS_KEY);
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw) as MCQTopicProgress[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function setLocalProgress(items: MCQTopicProgress[]) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(LOCAL_PROGRESS_KEY, JSON.stringify(items));
}

function buildRecord(draft: MCQAttemptDraft, userId: string | null): MCQAttemptRecord {
  return {
    id: generateId(),
    user_id: userId,
    topic_id: draft.topicId,
    started_at: draft.startedAt,
    completed_at: draft.completedAt,
    total_questions: draft.totalQuestions,
    correct_answers: draft.correctAnswers,
    score_percent: draft.scorePercent,
    answers: draft.answers,
    feedback_summary: draft.feedbackSummary,
    created_at: new Date().toISOString(),
  };
}

function computeProgress(attempts: MCQAttemptRecord[]): MCQTopicProgress[] {
  const buckets = new Map<string, MCQAttemptRecord[]>();
  for (const attempt of attempts) {
    const list = buckets.get(attempt.topic_id) ?? [];
    list.push(attempt);
    buckets.set(attempt.topic_id, list);
  }

  const result: MCQTopicProgress[] = [];
  for (const [topicId, topicAttempts] of Array.from(buckets.entries())) {
    const ordered = [...topicAttempts].sort((a, b) => (a.completed_at > b.completed_at ? -1 : 1));
    const attemptsCount = ordered.length;
    const bestScore = Math.max(...ordered.map((attempt) => attempt.score_percent));
    const latestScore = ordered[0]?.score_percent ?? 0;
    const averageScore = ordered.reduce((sum, attempt) => sum + attempt.score_percent, 0) / attemptsCount;
    const lastAttemptAt = ordered[0]?.completed_at ?? new Date().toISOString();

    result.push({
      topic_id: topicId,
      attempts_count: attemptsCount,
      best_score: bestScore,
      average_score: averageScore,
      latest_score: latestScore,
      last_attempt_at: lastAttemptAt,
    });
  }

  return result.sort((a, b) => (a.topic_id > b.topic_id ? 1 : -1));
}

async function getSignedInUserId(): Promise<string | null> {
  const client = getSupabaseClient();
  if (!client) {
    return null;
  }
  const { data } = await client.auth.getUser();
  return data.user?.id ?? null;
}

async function upsertSupabaseProgress(progress: MCQTopicProgress[], userId: string) {
  const client = getSupabaseClient();
  if (!client || progress.length === 0) {
    return;
  }

  const payload = progress.map((entry) => ({
    user_id: userId,
    topic_id: entry.topic_id,
    attempts_count: entry.attempts_count,
    best_score: entry.best_score,
    average_score: entry.average_score,
    latest_score: entry.latest_score,
    last_attempt_at: entry.last_attempt_at,
  }));

  const progressTable = client.from("mcq_topic_progress" as any) as any;
  await progressTable.upsert(payload, { onConflict: "user_id,topic_id" });
}

export async function persistMcqAttempt(draft: MCQAttemptDraft): Promise<MCQAttemptRecord> {
  const userId = await getSignedInUserId();
  const localRecord = buildRecord(draft, userId);

  const localAttempts = [localRecord, ...getLocalAttempts()];
  setLocalAttempts(localAttempts);

  const recomputed = computeProgress(localAttempts);
  setLocalProgress(recomputed);

  const client = getSupabaseClient();
  if (client && userId) {
    const attemptsTable = client.from("mcq_attempts" as any) as any;
    const payload = {
      user_id: userId,
      topic_id: localRecord.topic_id,
      started_at: localRecord.started_at,
      completed_at: localRecord.completed_at,
      total_questions: localRecord.total_questions,
      correct_answers: localRecord.correct_answers,
      score_percent: localRecord.score_percent,
      answers: localRecord.answers,
      feedback_summary: localRecord.feedback_summary,
    };

    const { data, error } = await attemptsTable.insert(payload).select("*").single();

    if (!error && data) {
      await upsertSupabaseProgress(recomputed, userId);
      const merged = {
        ...localRecord,
        ...(data as Record<string, unknown>),
      } as MCQAttemptRecord;
      const updatedLocal = [merged, ...getLocalAttempts().filter((item) => item.id !== localRecord.id)];
      setLocalAttempts(updatedLocal);
      return merged;
    }
  }

  return localRecord;
}

export async function listMcqTopicProgress(): Promise<MCQTopicProgress[]> {
  const local = getLocalProgress();
  const client = getSupabaseClient();
  const userId = await getSignedInUserId();

  if (!client || !userId) {
    return local;
  }

  const progressTable = client.from("mcq_topic_progress" as any) as any;
  const { data, error } = await progressTable
    .select("*")
    .eq("user_id", userId)
    .order("topic_id", { ascending: true });

  if (error || !data) {
    return local;
  }

  const records = data as Array<{
    topic_id: string;
    attempts_count: number;
    best_score: number;
    average_score: number;
    latest_score: number;
    last_attempt_at: string;
  }>;

  const mapped: MCQTopicProgress[] = records.map((entry) => ({
    topic_id: entry.topic_id,
    attempts_count: entry.attempts_count,
    best_score: Number(entry.best_score) || 0,
    average_score: Number(entry.average_score) || 0,
    latest_score: Number(entry.latest_score) || 0,
    last_attempt_at: entry.last_attempt_at,
  }));

  setLocalProgress(mapped);
  return mapped;
}

export async function listRecentMcqAttempts(limit = 5): Promise<MCQAttemptRecord[]> {
  const local = getLocalAttempts().slice(0, limit);
  const client = getSupabaseClient();
  const userId = await getSignedInUserId();

  if (!client || !userId) {
    return local;
  }

  const attemptsTable = client.from("mcq_attempts" as any) as any;
  const { data, error } = await attemptsTable
    .select("*")
    .eq("user_id", userId)
    .order("completed_at", { ascending: false })
    .limit(limit);

  if (error || !data) {
    return local;
  }

  const mapped = (data as MCQAttemptRecord[]).map((entry) => ({
    ...entry,
    score_percent: Number(entry.score_percent) || 0,
  }));

  const merged = [...mapped, ...getLocalAttempts()].sort((a, b) => (a.completed_at > b.completed_at ? -1 : 1));
  setLocalAttempts(merged);

  return mapped;
}
