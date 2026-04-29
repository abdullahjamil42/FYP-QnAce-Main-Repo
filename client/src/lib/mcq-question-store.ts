export type QuizQuestion = {
  id: string;
  prompt: string;
  options: Array<{ id: string; text: string }>;
  correctOptionId: string;
  explanation: string;
  subtopic: string;
  difficulty: "easy" | "medium" | "hard";
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

export async function fetchMcqCatalog(): Promise<CatalogResponse> {
  const response = await fetch("/api/mcq/catalog", { cache: "no-store" });
  if (!response.ok) {
    return { topics: [], subtopics: [] };
  }
  return (await response.json()) as CatalogResponse;
}

export async function fetchQuizQuestions(params: {
  topicId: string;
  subtopic: string;
  difficulty: "easy" | "medium" | "hard" | "random";
  count: number;
  mixAcrossTopics?: boolean;
}): Promise<QuizQuestion[]> {
  const search = new URLSearchParams();
  if (params.mixAcrossTopics) {
    search.set("mix", "true");
  } else {
    search.set("topicId", params.topicId);
    search.set("subtopic", params.subtopic);
  }
  search.set("difficulty", params.difficulty);
  search.set("count", String(params.count));

  const response = await fetch(`/api/mcq/quiz?${search.toString()}`, { cache: "no-store" });
  if (!response.ok) {
    return [];
  }
  const data = (await response.json()) as { questions?: QuizQuestion[] };
  return Array.isArray(data.questions) ? data.questions : [];
}
