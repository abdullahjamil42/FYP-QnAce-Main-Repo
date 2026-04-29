import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

export const runtime = "nodejs";

type ManifestEntry = {
  topic_id: string;
  topic: string;
  num_questions: number;
  file: string;
};

type TopicFile = {
  topic_id: string;
  topic: string;
  total: number;
  breakdown: Record<string, number>;
  subtopics: string[];
  questions: unknown[];
};

export type CatalogTopicEntry = {
  id: string;
  title: string;
  defaultQuestions: number;
  subtopicCount: number;
};

export type CatalogSubtopicEntry = {
  topic_id: string;
  title: string;
};

export type CatalogResponse = {
  topics: CatalogTopicEntry[];
  subtopics: CatalogSubtopicEntry[];
};

let cache: { value: CatalogResponse; loadedAt: number } | null = null;
const CACHE_TTL_MS = 5 * 60 * 1000;

function getDataDir(): string {
  return (
    process.env.QACE_MCQ_DATA_DIR ??
    path.join(process.cwd(), "..", "data", "mcq_generated")
  );
}

async function readTopicFile(dir: string, file: string): Promise<TopicFile | null> {
  try {
    const full = path.join(dir, file);
    const raw = await fs.readFile(full, "utf-8");
    return JSON.parse(raw) as TopicFile;
  } catch {
    return null;
  }
}

async function buildCatalog(): Promise<CatalogResponse> {
  const dir = getDataDir();
  const manifestPath = path.join(dir, "manifest.json");
  const manifestRaw = await fs.readFile(manifestPath, "utf-8");
  const manifest = JSON.parse(manifestRaw) as ManifestEntry[];

  const topicFiles = await Promise.all(
    manifest.map((entry) => readTopicFile(dir, path.basename(entry.file))),
  );

  const topics: CatalogTopicEntry[] = [];
  const subtopics: CatalogSubtopicEntry[] = [];

  for (let i = 0; i < manifest.length; i += 1) {
    const entry = manifest[i];
    const file = topicFiles[i];
    const subList = file?.subtopics ?? [];
    topics.push({
      id: entry.topic_id,
      title: file?.topic ?? entry.topic,
      defaultQuestions: file?.total ?? entry.num_questions,
      subtopicCount: subList.length,
    });
    for (const sub of subList) {
      subtopics.push({ topic_id: entry.topic_id, title: sub });
    }
  }

  topics.sort((a, b) => a.title.localeCompare(b.title));
  return { topics, subtopics };
}

export async function GET() {
  try {
    const now = Date.now();
    if (cache && now - cache.loadedAt < CACHE_TTL_MS) {
      return NextResponse.json(cache.value);
    }
    const value = await buildCatalog();
    cache = { value, loadedAt: now };
    return NextResponse.json(value);
  } catch (err) {
    const message = err instanceof Error ? err.message : "unknown error";
    return NextResponse.json(
      { error: `Failed to load MCQ catalog: ${message}` },
      { status: 500 },
    );
  }
}
