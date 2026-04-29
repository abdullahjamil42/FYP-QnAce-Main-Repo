import { NextRequest, NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

export const runtime = "nodejs";

type Difficulty = "easy" | "medium" | "hard";

type RawQuestion = {
  subtopic: string;
  difficulty: Difficulty;
  question: string;
  options: string[];
  answer: string;
  explanation: string;
};

type TopicFile = {
  topic_id: string;
  topic: string;
  subtopics: string[];
  questions: RawQuestion[];
};

type ManifestEntry = {
  topic_id: string;
  topic: string;
  num_questions: number;
  file: string;
};

const OPTION_IDS = ["a", "b", "c", "d"] as const;

export type QuizQuestion = {
  id: string;
  prompt: string;
  options: Array<{ id: string; text: string }>;
  correctOptionId: string;
  explanation: string;
  subtopic: string;
  difficulty: Difficulty;
};

const topicCache = new Map<string, { value: TopicFile; loadedAt: number }>();
let manifestCache: { value: ManifestEntry[]; loadedAt: number } | null = null;
const CACHE_TTL_MS = 5 * 60 * 1000;

function getDataDir(): string {
  return (
    process.env.QACE_MCQ_DATA_DIR ??
    path.join(process.cwd(), "..", "data", "mcq_generated")
  );
}

async function readManifest(): Promise<ManifestEntry[]> {
  const now = Date.now();
  if (manifestCache && now - manifestCache.loadedAt < CACHE_TTL_MS) {
    return manifestCache.value;
  }
  const dir = getDataDir();
  const raw = await fs.readFile(path.join(dir, "manifest.json"), "utf-8");
  const value = JSON.parse(raw) as ManifestEntry[];
  manifestCache = { value, loadedAt: now };
  return value;
}

async function readTopic(topicId: string): Promise<TopicFile | null> {
  const now = Date.now();
  const cached = topicCache.get(topicId);
  if (cached && now - cached.loadedAt < CACHE_TTL_MS) {
    return cached.value;
  }
  const manifest = await readManifest();
  const entry = manifest.find((e) => e.topic_id === topicId);
  if (!entry) return null;
  const dir = getDataDir();
  try {
    const raw = await fs.readFile(path.join(dir, path.basename(entry.file)), "utf-8");
    const value = JSON.parse(raw) as TopicFile;
    topicCache.set(topicId, { value, loadedAt: now });
    return value;
  } catch {
    return null;
  }
}

function shuffle<T>(items: T[]): T[] {
  const arr = items.slice();
  for (let i = arr.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

function toQuizQuestion(row: RawQuestion, topicId: string, index: number): QuizQuestion {
  const options = Array.isArray(row.options) ? row.options : [];
  const optionItems = options.slice(0, 4).map((text, i) => ({
    id: OPTION_IDS[i] ?? `${i}`,
    text: String(text),
  }));
  const match = optionItems.find((item) => item.text === row.answer);
  const fallback = optionItems[0]?.id ?? "a";
  return {
    id: `${topicId}-${index}`,
    prompt: row.question,
    options: optionItems,
    correctOptionId: match?.id ?? fallback,
    explanation: row.explanation ?? "",
    subtopic: row.subtopic,
    difficulty: row.difficulty,
  };
}

function filterPool(
  topic: TopicFile,
  subtopic: string,
  difficulty: "easy" | "medium" | "hard" | "random",
): Array<{ row: RawQuestion; index: number }> {
  const pool: Array<{ row: RawQuestion; index: number }> = [];
  for (let i = 0; i < topic.questions.length; i += 1) {
    const row = topic.questions[i];
    if (difficulty !== "random" && row.difficulty !== difficulty) continue;
    if (subtopic !== "All Topics" && row.subtopic !== subtopic) continue;
    pool.push({ row, index: i });
  }
  return pool;
}

async function pickFromTopic(
  topicId: string,
  subtopic: string,
  difficulty: "easy" | "medium" | "hard" | "random",
  count: number,
): Promise<QuizQuestion[]> {
  const topic = await readTopic(topicId);
  if (!topic) return [];
  const pool = filterPool(topic, subtopic, difficulty);
  return shuffle(pool)
    .slice(0, count)
    .map(({ row, index }) => toQuizQuestion(row, topicId, index));
}

async function pickMixed(
  difficulty: "easy" | "medium" | "hard" | "random",
  count: number,
): Promise<QuizQuestion[]> {
  const manifest = await readManifest();
  const topicIds = shuffle(manifest.map((e) => e.topic_id));
  if (topicIds.length === 0) return [];

  const basePerTopic = Math.floor(count / topicIds.length);
  let remainder = count % topicIds.length;
  const targetByTopic = new Map<string, number>();
  for (const topicId of topicIds) {
    const extra = remainder > 0 ? 1 : 0;
    if (remainder > 0) remainder -= 1;
    targetByTopic.set(topicId, basePerTopic + extra);
  }

  const perTopic = await Promise.all(
    topicIds.map(async (topicId) => {
      const topic = await readTopic(topicId);
      if (!topic) return [] as QuizQuestion[];
      const pool = filterPool(topic, "All Topics", difficulty);
      return shuffle(pool).map(({ row, index }) => toQuizQuestion(row, topicId, index));
    }),
  );

  const selected: QuizQuestion[] = [];
  const leftovers: QuizQuestion[] = [];
  for (let i = 0; i < topicIds.length; i += 1) {
    const target = targetByTopic.get(topicIds[i]) ?? 0;
    const rows = perTopic[i] ?? [];
    selected.push(...rows.slice(0, target));
    leftovers.push(...rows.slice(target));
  }

  if (selected.length < count) {
    const seen = new Set(selected.map((q) => q.id));
    const filler = shuffle(leftovers).filter((q) => !seen.has(q.id));
    selected.push(...filler.slice(0, count - selected.length));
  }

  return shuffle(selected).slice(0, count);
}

export async function GET(req: NextRequest) {
  try {
    const url = new URL(req.url);
    const topicId = url.searchParams.get("topicId") ?? "";
    const subtopic = url.searchParams.get("subtopic") ?? "All Topics";
    const difficulty = (url.searchParams.get("difficulty") ?? "random") as
      | "easy"
      | "medium"
      | "hard"
      | "random";
    const count = Math.max(1, Math.min(200, Number(url.searchParams.get("count") ?? "10")));
    const mix = url.searchParams.get("mix") === "true";

    const questions = mix
      ? await pickMixed(difficulty, count)
      : await pickFromTopic(topicId, subtopic, difficulty, count);

    return NextResponse.json({ questions });
  } catch (err) {
    const message = err instanceof Error ? err.message : "unknown error";
    return NextResponse.json(
      { error: `Failed to load MCQ quiz: ${message}` },
      { status: 500 },
    );
  }
}
