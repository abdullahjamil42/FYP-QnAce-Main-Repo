import { getSupabaseClient } from "@/lib/supabase";

export type DBMcqQuestion = {
  id: string;
  topic_id: string;
  subtopic_title: string;
  difficulty: "easy" | "medium" | "hard";
  question: string;
  options: string[];
  answer: string;
  explanation: string;
};

export type QuizQuestion = {
  id: string;
  prompt: string;
  options: Array<{ id: string; text: string }>;
  correctOptionId: string;
  explanation: string;
  subtopic: string;
  difficulty: "easy" | "medium" | "hard";
};

const OPTION_IDS = ["a", "b", "c", "d"] as const;

function shuffle<T>(items: T[]): T[] {
  const arr = [...items];
  for (let i = arr.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

function toQuizQuestion(row: DBMcqQuestion): QuizQuestion {
  const options = Array.isArray(row.options) ? row.options : [];
  const optionItems = options.slice(0, 4).map((text, index) => ({
    id: OPTION_IDS[index] ?? `${index}`,
    text: String(text),
  }));

  const match = optionItems.find((item) => item.text === row.answer);
  const fallback = optionItems[0]?.id ?? "a";

  return {
    id: row.id,
    prompt: row.question,
    options: optionItems,
    correctOptionId: match?.id ?? fallback,
    explanation: row.explanation ?? "",
    subtopic: row.subtopic_title,
    difficulty: row.difficulty,
  };
}

export async function fetchQuizQuestions(params: {
  topicId: string;
  subtopic: string;
  difficulty: "easy" | "medium" | "hard";
  count: number;
}): Promise<QuizQuestion[]> {
  const client = getSupabaseClient();
  if (!client) {
    return [];
  }

  const table = client.from("mcq_questions" as any) as any;
  let query = table
    .select("id,topic_id,subtopic_title,difficulty,question,options,answer,explanation")
    .eq("topic_id", params.topicId)
    .eq("difficulty", params.difficulty)
    .limit(Math.max(params.count * 4, 40));

  if (params.subtopic !== "All Topics") {
    query = query.eq("subtopic_title", params.subtopic);
  }

  const { data, error } = await query;
  if (error || !Array.isArray(data)) {
    return [];
  }

  const rows = data as DBMcqQuestion[];
  const picked = shuffle(rows).slice(0, params.count);
  return picked.map(toQuizQuestion);
}
