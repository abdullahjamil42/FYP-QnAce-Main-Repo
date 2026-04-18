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
  difficulty: "easy" | "medium" | "hard" | "random";
  count: number;
  mixAcrossTopics?: boolean;
}): Promise<QuizQuestion[]> {
  const client = getSupabaseClient();
  if (!client) {
    return [];
  }

  if (params.mixAcrossTopics) {
    const topicsTable = client.from("mcq_topics" as any) as any;
    const { data: topics, error: topicError } = await topicsTable.select("id").eq("is_active", true);
    if (topicError || !Array.isArray(topics) || topics.length === 0) {
      return [];
    }

    const topicIds = shuffle(
      topics
        .map((topic) => String((topic as { id?: string }).id ?? "").trim())
        .filter((id) => id.length > 0)
    );
    if (topicIds.length === 0) {
      return [];
    }

    const basePerTopic = Math.floor(params.count / topicIds.length);
    let remainder = params.count % topicIds.length;
    const targetByTopic = new Map<string, number>();
    for (const topicId of topicIds) {
      const extra = remainder > 0 ? 1 : 0;
      if (remainder > 0) {
        remainder -= 1;
      }
      targetByTopic.set(topicId, basePerTopic + extra);
    }

    const perTopicPoolLimit = Math.max(20, Math.ceil((params.count / topicIds.length) * 5));

    const rowsByTopic = await Promise.all(
      topicIds.map(async (topicId) => {
        const table = client.from("mcq_questions" as any) as any;

        // Get total count for this topic so we can pick a random offset
        let countQuery = (client.from("mcq_questions" as any) as any)
          .select("id", { count: "exact", head: true })
          .eq("topic_id", topicId);
        if (params.difficulty !== "random") {
          countQuery = countQuery.eq("difficulty", params.difficulty);
        }
        const { count: totalCount } = await countQuery;
        const maxOffset = Math.max(0, (totalCount ?? 0) - perTopicPoolLimit);
        const randomOffset = Math.floor(Math.random() * (maxOffset + 1));

        let query = table
          .select("id,topic_id,subtopic_title,difficulty,question,options,answer,explanation")
          .eq("topic_id", topicId)
          .range(randomOffset, randomOffset + perTopicPoolLimit - 1);

        if (params.difficulty !== "random") {
          query = query.eq("difficulty", params.difficulty);
        }

        const { data, error } = await query;

        if (error || !Array.isArray(data)) {
          return [] as DBMcqQuestion[];
        }

        return shuffle(data as DBMcqQuestion[]);
      })
    );

    const selected: DBMcqQuestion[] = [];
    const leftovers: DBMcqQuestion[] = [];

    for (let i = 0; i < topicIds.length; i += 1) {
      const topicRows = rowsByTopic[i] ?? [];
      const target = targetByTopic.get(topicIds[i]) ?? 0;
      selected.push(...topicRows.slice(0, target));
      leftovers.push(...topicRows.slice(target));
    }

    if (selected.length < params.count) {
      const selectedIds = new Set(selected.map((row) => row.id));
      const filler = shuffle(leftovers).filter((row) => !selectedIds.has(row.id));
      selected.push(...filler.slice(0, params.count - selected.length));
    }

    return shuffle(selected)
      .slice(0, params.count)
      .map(toQuizQuestion);
  }

  const table = client.from("mcq_questions" as any) as any;
  const pool = Math.max(params.count * 4, 40);

  // Get total count so we can pick a random offset into the result set
  let countQuery = (client.from("mcq_questions" as any) as any)
    .select("id", { count: "exact", head: true })
    .eq("topic_id", params.topicId);
  if (params.difficulty !== "random") {
    countQuery = countQuery.eq("difficulty", params.difficulty);
  }
  if (params.subtopic !== "All Topics") {
    countQuery = countQuery.eq("subtopic_title", params.subtopic);
  }
  const { count: totalCount } = await countQuery;
  const maxOffset = Math.max(0, (totalCount ?? 0) - pool);
  const randomOffset = Math.floor(Math.random() * (maxOffset + 1));

  let query = table
    .select("id,topic_id,subtopic_title,difficulty,question,options,answer,explanation")
    .eq("topic_id", params.topicId)
    .range(randomOffset, randomOffset + pool - 1);

  if (params.difficulty !== "random") {
    query = query.eq("difficulty", params.difficulty);
  }

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
