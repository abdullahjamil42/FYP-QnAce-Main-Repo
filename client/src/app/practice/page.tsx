"use client";

import Link from "next/link";
import { useMemo, useState, useEffect } from "react";
import { type User } from "@supabase/supabase-js";
import AppShell from "@/components/AppShell";
import { Badge, GlassCard, ProgressRow } from "@/components/ui";
import { getQuestionsForTopic } from "@/lib/mcq-bank";
import { getSupabaseClient } from "@/lib/supabase";
import { fetchQuizQuestions, type QuizQuestion } from "@/lib/mcq-question-store";
import {
  listMcqTopicProgress,
  listRecentMcqAttempts,
  persistMcqAttempt,
  type MCQAttemptAnswer,
  type MCQAttemptRecord,
  type MCQTopicProgress,
} from "@/lib/mcq-progress-store";
import { listNoteFolders, listFolderFiles, getNoteByFile, preprocessNoteContent, type NoteSection } from "@/lib/notes";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import type { Components } from "react-markdown";

const QUESTIONS_PER_RUN = 4;
const MIXED_TOPIC_ID = "__mixed__";

/** Custom ReactMarkdown components for styled study notes */
const mdComponents: Components = {
  // Syntax-highlighted code blocks
  code({ node, className, children, ...props }) {
    const match = /language-(\w+)/.exec(className ?? "");
    const isBlock = match !== null;
    if (isBlock) {
      return (
        <SyntaxHighlighter
          style={vscDarkPlus as Record<string, React.CSSProperties>}
          language={match[1]}
          PreTag="div"
          customStyle={{
            borderRadius: "12px",
            fontSize: "0.82rem",
            margin: "1.25rem 0",
            padding: "1.25rem 1.5rem",
            overflowX: "auto",
          }}
          codeTagProps={{ style: { fontFamily: "'Fira Code', 'Cascadia Code', monospace" } }}
        >
          {String(children).replace(/\n$/, "")}
        </SyntaxHighlighter>
      );
    }
    return (
      <code className="bg-blue-50 text-blue-800 px-1.5 py-0.5 rounded text-sm font-mono border border-blue-100" {...props}>
        {children}
      </code>
    );
  },
  // Callout blockquotes (⚠️ Interview Gotcha, 💡 Tip, 📌 Must-Know)
  blockquote({ children }) {
    const text = String(children ?? "");
    const isWarning = /⚠/.test(text);
    const isTip     = /💡/.test(text);
    const bg = isWarning
      ? "bg-amber-50 border-amber-400"
      : isTip
      ? "bg-green-50 border-green-400"
      : "bg-blue-50 border-blue-400";
    return (
      <div className={`my-4 rounded-xl border-l-4 px-5 py-3 ${bg} not-prose`}>
        <p className="text-sm leading-relaxed text-gray-800">{children}</p>
      </div>
    );
  },
  // Large section heading (## → h2)
  h2({ children }) {
    return (
      <h2 className="flex items-center gap-2 text-xl font-bold text-indigo-700 mt-8 mb-3 pb-2 border-b-2 border-indigo-100 not-prose">
        {children}
      </h2>
    );
  },
  // Sub-heading (### → h3)
  h3({ children }) {
    return (
      <h3 className="text-base font-bold text-gray-800 mt-5 mb-2 not-prose">
        {children}
      </h3>
    );
  },
  // Paragraphs
  p({ children }) {
    return <p className="text-gray-700 leading-relaxed mb-3 text-[0.95rem]">{children}</p>;
  },
  // Lists
  ul({ children }) {
    return <ul className="list-disc list-outside ml-5 space-y-1 mb-3 text-gray-700 text-[0.95rem]">{children}</ul>;
  },
  ol({ children }) {
    return <ol className="list-decimal list-outside ml-5 space-y-1 mb-3 text-gray-700 text-[0.95rem]">{children}</ol>;
  },
  li({ children }) {
    return <li className="leading-relaxed pl-1">{children}</li>;
  },
  // Strong / bold
  strong({ children }) {
    return <strong className="font-semibold text-gray-900">{children}</strong>;
  },
};

function cleanQuestionPrompt(prompt: string): string {
  return prompt.replace(/^\[[^\]]+\]\s*/, "").trim();
}

function getFeedback(score: number) {
  if (score >= 85) {
    return "Excellent consistency. Keep increasing question speed while preserving reasoning quality.";
  }
  if (score >= 65) {
    return "Good base. Review the explanations for missed questions and retry this topic for mastery.";
  }
  return "Build fundamentals first. Reattempt this topic after reading each explanation carefully.";
}

type QuizState = "topic-selection" | "running" | "completed";

type Note = {
  id: string;
  topic: string;
  notes_markdown: string;
  updated_at: string;
};

type CatalogTopic = {
  id: string;
  title: string;
  default_questions: number;
};

type CatalogSubtopic = {
  topic_id: string;
  title: string;
};

export default function PracticePage() {
  const supabase = getSupabaseClient();
  const [mode, setMode] = useState<"quiz" | "study">("study");
  const [quizState, setQuizState] = useState<QuizState>("topic-selection");
  const [activeTopicId, setActiveTopicId] = useState<string>("technical");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [startedAt, setStartedAt] = useState<string | null>(null);
  const [lastAttempt, setLastAttempt] = useState<MCQAttemptRecord | null>(null);
  const [topicProgress, setTopicProgress] = useState<MCQTopicProgress[]>([]);
  const [recentAttempts, setRecentAttempts] = useState<MCQAttemptRecord[]>([]);
  const [catalogTopics, setCatalogTopics] = useState<Array<{ id: string; title: string; subtopicCount: number; defaultQuestions: number }>>([]);
  const [catalogSubtopics, setCatalogSubtopics] = useState<CatalogSubtopic[]>([]);
  const [selectedCatalogTopicId, setSelectedCatalogTopicId] = useState<string | null>(null);
  const [selectedSubtopic, setSelectedSubtopic] = useState<string>("All Topics");
  const [subtopicSearch, setSubtopicSearch] = useState("");
  const [selectedQuestionCount, setSelectedQuestionCount] = useState<number>(10);
  const [selectedAnswerMode, setSelectedAnswerMode] = useState<"each" | "end">("end");
  const [selectedTimeMode, setSelectedTimeMode] = useState<"per-question" | "total" | "unlimited">("unlimited");
  const [selectedDifficulty, setSelectedDifficulty] = useState<"easy" | "medium" | "hard" | "random">("medium");
  const [quizConfigNotice, setQuizConfigNotice] = useState<string>("");
  const [liveQuestions, setLiveQuestions] = useState<QuizQuestion[]>([]);

  // Notes state
  const [user, setUser] = useState<User | null>(null);
  const [bucketTopics, setBucketTopics] = useState<{ folder: string; label: string }[]>([]);
  const [bucketTopicsLoading, setBucketTopicsLoading] = useState(false);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [folderFiles, setFolderFiles] = useState<{ path: string; label: string }[]>([]);
  const [folderFilesLoading, setFolderFilesLoading] = useState(false);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [loadingNotes, setLoadingNotes] = useState<Record<string, boolean>>({});
  const [selectedStudyTopic, setSelectedStudyTopic] = useState<string | null>(null);
  const [parsedSections, setParsedSections] = useState<NoteSection[]>([]);
  const [selectedSectionIdx, setSelectedSectionIdx] = useState(0);

  const [shuffleSeed, setShuffleSeed] = useState(0);

  const questions = useMemo(() => {
    if (liveQuestions.length > 0) {
      return liveQuestions;
    }

    const all = getQuestionsForTopic(activeTopicId);
    const shuffled = [...all].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, QUESTIONS_PER_RUN).map((question) => ({
      id: question.id,
      prompt: question.prompt,
      options: question.options,
      correctOptionId: question.correctOptionId,
      explanation: question.explanation,
      subtopic: question.topicId,
      difficulty: "medium" as const,
    }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTopicId, liveQuestions, shuffleSeed]);

  const currentQuestion = questions[currentIndex];
  const selectedOptionId = currentQuestion ? answers[currentQuestion.id] : undefined;

  const answeredCount = Object.keys(answers).length;
  const completionPercent = questions.length === 0 ? 0 : (answeredCount / questions.length) * 100;

  const topicProgressMap = useMemo(() => {
    const map = new Map<string, MCQTopicProgress>();
    for (const item of topicProgress) {
      map.set(item.topic_id, item);
    }
    return map;
  }, [topicProgress]);

  useEffect(() => {
    let cancelled = false;
    async function loadData() {
      if (!supabase) return;
      const [progress, attempts, { data: authData }] = await Promise.all([
        listMcqTopicProgress(),
        listRecentMcqAttempts(5),
        supabase.auth.getUser(),
      ]);

      if (cancelled) return;

      setUser(authData.user);

      let catalog: Array<{ id: string; title: string; subtopicCount: number; defaultQuestions: number }> = [];
      let loadedSubtopics: CatalogSubtopic[] = [];
      const topicsTable = supabase.from("mcq_topics" as any) as any;
      const subtopicsTable = supabase.from("mcq_subtopics" as any) as any;
      const [{ data: topics }, { data: subtopics }] = await Promise.all([
        topicsTable.select("id,title,default_questions").eq("is_active", true).order("title", { ascending: true }),
        subtopicsTable.select("topic_id,title").eq("is_active", true),
      ]);

      const topicRows = (topics ?? []) as CatalogTopic[];
      const subtopicRows = (subtopics ?? []) as CatalogSubtopic[];
      loadedSubtopics = subtopicRows;
      const counts = new Map<string, number>();
      for (const row of subtopicRows) {
        counts.set(row.topic_id, (counts.get(row.topic_id) ?? 0) + 1);
      }

      catalog = topicRows.map((topic) => ({
        id: topic.id,
        title: topic.title,
        subtopicCount: counts.get(topic.id) ?? 0,
        defaultQuestions: topic.default_questions ?? 1000,
      }));

      if (!cancelled) {
        setTopicProgress(progress);
        setRecentAttempts(attempts);
        setCatalogTopics(catalog);
        setCatalogSubtopics(loadedSubtopics);
      }
    }
    void loadData();
    return () => {
      cancelled = true;
    };
  }, [supabase]);


  const handleSelectFolder = async (folder: string) => {
    if (selectedFolder === folder) return;
    setSelectedFolder(folder);
    setSelectedStudyTopic(null);
    setParsedSections([]);
    setFolderFiles([]);
    setFolderFilesLoading(true);
    const files = await listFolderFiles(folder);
    setFolderFiles(files);
    setFolderFilesLoading(false);
    // Auto-select first file
    if (files.length > 0) void handleSelectStudyTopic(files[0].path);
  };

  const handleSelectStudyTopic = async (path: string) => {
    setSelectedStudyTopic(path);
    setSelectedSectionIdx(0);
    if (notes[path]) return;
    setLoadingNotes((prev) => ({ ...prev, [path]: true }));
    const note = await getNoteByFile(path);
    if (note) setNotes((prev) => ({ ...prev, [path]: note }));
    setLoadingNotes((prev) => ({ ...prev, [path]: false }));
  };

  // Load bucket folders when entering study mode
  useEffect(() => {
    if (mode === "study" && bucketTopics.length === 0) {
      setBucketTopicsLoading(true);
      void listNoteFolders().then((topics) => {
        setBucketTopics(topics);
        setBucketTopicsLoading(false);
        // Auto-select first folder
        if (topics.length > 0) void handleSelectFolder(topics[0].folder);
      });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  function startTopicQuiz(topicId: string) {
    setActiveTopicId(topicId);
    setAnswers({});
    setCurrentIndex(0);
    setLastAttempt(null);
    setLiveQuestions([]);
    setShuffleSeed((prev) => prev + 1);
    setStartedAt(new Date().toISOString());
    setQuizState("running");
  }

  function selectAnswer(questionId: string, optionId: string) {
    setAnswers((prev) => ({
      ...prev,
      [questionId]: optionId,
    }));
  }

  async function nextOrFinish() {
    if (!currentQuestion || !selectedOptionId || !startedAt) {
      return;
    }

    const isLastQuestion = currentIndex >= questions.length - 1;
    if (!isLastQuestion) {
      setCurrentIndex((value) => value + 1);
      return;
    }

    const attemptAnswers: MCQAttemptAnswer[] = questions.map((question) => {
      const selected = answers[question.id] ?? "";
      return {
        questionId: question.id,
        selectedOptionId: selected,
        correctOptionId: question.correctOptionId,
        isCorrect: selected === question.correctOptionId,
      };
    });

    const correctAnswers = attemptAnswers.filter((item) => item.isCorrect).length;
    const scorePercent = questions.length === 0 ? 0 : (correctAnswers / questions.length) * 100;
    const feedbackSummary = getFeedback(scorePercent);

    const saved = await persistMcqAttempt({
      topicId: activeTopicId,
      startedAt,
      completedAt: new Date().toISOString(),
      totalQuestions: questions.length,
      correctAnswers,
      scorePercent,
      answers: attemptAnswers,
      feedbackSummary,
    });

    const [progress, attempts] = await Promise.all([listMcqTopicProgress(), listRecentMcqAttempts(5)]);
    setTopicProgress(progress);
    setRecentAttempts(attempts);
    setLastAttempt(saved);
    setQuizState("completed");
  }

  function retakeTopic() {
    setAnswers({});
    setCurrentIndex(0);
    setLastAttempt(null);
    setShuffleSeed((prev) => prev + 1);
    setLiveQuestions([]);
    setStartedAt(new Date().toISOString());
    setQuizState("running");
  }



  const selectedCatalogTopic = useMemo(() => {
    if (!selectedCatalogTopicId) {
      return null;
    }
    if (selectedCatalogTopicId === MIXED_TOPIC_ID) {
      return {
        id: MIXED_TOPIC_ID,
        title: "Mixed Topics",
        subtopicCount: catalogTopics.length,
        defaultQuestions: 1000,
      };
    }
    return catalogTopics.find((topic) => topic.id === selectedCatalogTopicId) ?? null;
  }, [catalogTopics, selectedCatalogTopicId]);

  const selectedTopicSubtopics = useMemo(() => {
    if (!selectedCatalogTopicId || selectedCatalogTopicId === MIXED_TOPIC_ID) {
      return [] as string[];
    }
    return catalogSubtopics
      .filter((row) => row.topic_id === selectedCatalogTopicId)
      .map((row) => row.title)
      .filter((title) => title.toLowerCase().includes(subtopicSearch.trim().toLowerCase()));
  }, [catalogSubtopics, selectedCatalogTopicId, subtopicSearch]);

  function openTopicConfig(topicId: string) {
    setSelectedCatalogTopicId(topicId);
    setQuizConfigNotice("");
    setSelectedSubtopic("All Topics");
    setSubtopicSearch("");
    setSelectedQuestionCount(10);
    setSelectedDifficulty("medium");
    setSelectedAnswerMode("end");
    setSelectedTimeMode("unlimited");
  }

  return (
    <AppShell
      title="Prepare and Practice"
      subtitle="Pick a topic, Access Notes, attempt MCQs, and track your learning progress feedback."
      actions={
        <Link href="/session/live" className="rounded-full border border-gray-700/50 bg-blue-600 backdrop-blur-sm px-5 py-2.5 text-sm font-semibold text-gray-300 transition hover:bg-gray-700/60 hover:text-white">
          Start Full Mock
        </Link>
      }
    >
      <div className="flex justify-center mb-6">
        <div className="bg-gray-800/60 backdrop-blur-sm border border-gray-700/50 rounded-full p-1 flex gap-1">
          <button
            onClick={() => setMode("study")}
            className={`px-6 py-2 rounded-full text-sm font-semibold transition-all ${
              mode === "study"
                ? "bg-blue-600 text-white shadow-lg shadow-blue-600/30"
                : "text-gray-400 hover:text-gray-200 hover:bg-gray-700/60"
            }`}
          >
            Study Notes
          </button>
          <button
            onClick={() => setMode("quiz")}
            className={`px-6 py-2 rounded-full text-sm font-semibold transition-all ${
              mode === "quiz"
                ? "bg-blue-600 text-white shadow-lg shadow-blue-600/30"
                : "text-gray-400 hover:text-gray-200 hover:bg-gray-700/60"
            }`}
          >
            Quiz Catalog
          </button>
        </div>
      </div>

      {mode === "quiz" && quizState === "topic-selection" ? (
        <>
          <GlassCard className="mt-6 animate-fade-up">
            {catalogTopics.length === 0 ? (
              <p className="text-sm text-qace-muted">Loading...</p>
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-semibold">Topic Catalog</h3>
                  <Badge>{catalogTopics.length} topics</Badge>
                </div>
                <div className="mt-4 grid gap-2 md:grid-cols-2 lg:grid-cols-3">
                  <button
                    onClick={() => openTopicConfig(MIXED_TOPIC_ID)}
                    className="rounded-lg border border-sky-300/40 bg-sky-500/10 px-3 py-2 text-left transition hover:bg-sky-500/20"
                  >
                    <p className="text-sm font-semibold text-white">Mix (All Topics)</p>
                    <p className="text-xs text-qace-muted">Balanced random mix from all topics</p>
                  </button>
                  {catalogTopics.map((topic) => {
                    const progress = topicProgressMap.get(topic.id);
                    return (
                      <button
                        key={topic.id}
                        onClick={() => openTopicConfig(topic.id)}
                        className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-left transition hover:bg-white/10"
                      >
                        <p className="text-sm font-semibold text-white">{topic.title}</p>
                        <p className="text-xs text-qace-muted">{topic.subtopicCount} subtopics</p>
                        {progress ? <p className="mt-1 text-xs text-qace-muted">Best score: {progress.best_score.toFixed(0)}%</p> : null}
                      </button>
                    );
                  })}
                </div>
              </>
            )}
          </GlassCard>

          {selectedCatalogTopic ? (
            <GlassCard className="mt-6 animate-fade-up-delayed">
              <div className="flex items-center justify-between">
                <button
                  onClick={() => setSelectedCatalogTopicId(null)}
                  className="text-sm font-medium text-qace-muted transition hover:text-white"
                >
                  Back to topics
                </button>
                <Badge>{selectedCatalogTopic.subtopicCount} topics</Badge>
              </div>

              <div className="mt-4">
                <h2 className="text-2xl font-semibold text-white">{selectedCatalogTopic.title}</h2>
                <p className="mt-1 text-sm text-qace-muted">
                  {selectedCatalogTopic.defaultQuestions.toFixed(0)} questions · {selectedCatalogTopic.subtopicCount} topics
                </p>
              </div>

              <section className="mt-6">
                <p className="text-sm font-semibold text-white">1. Choose a Topic</p>
                {selectedCatalogTopic.id !== MIXED_TOPIC_ID ? (
                  <input
                    value={subtopicSearch}
                    onChange={(event) => setSubtopicSearch(event.target.value)}
                    placeholder="Search topics..."
                    className="mt-3 w-full rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-qace-muted outline-none focus:border-sky-300"
                  />
                ) : null}
                <div className="mt-3 grid gap-2 md:grid-cols-2 lg:grid-cols-3">
                  <button
                    onClick={() => setSelectedSubtopic("All Topics")}
                    className={`rounded-lg border px-3 py-2 text-left text-sm transition ${
                      selectedSubtopic === "All Topics"
                        ? "border-sky-300 bg-sky-500/20 text-white"
                        : "border-white/10 bg-white/5 text-qace-muted hover:bg-white/10 hover:text-white"
                    }`}
                  >
                    <p className="font-semibold">All Topics</p>
                    <p className="text-xs text-qace-muted">
                      {selectedCatalogTopic.id === MIXED_TOPIC_ID ? "Random across all topics" : `${selectedCatalogTopic.subtopicCount} topics`}
                    </p>
                  </button>
                  {selectedTopicSubtopics.map((title) => (
                    <button
                      key={title}
                      onClick={() => setSelectedSubtopic(title)}
                      className={`rounded-lg border px-3 py-2 text-left text-sm transition ${
                        selectedSubtopic === title
                          ? "border-sky-300 bg-sky-500/20 text-white"
                          : "border-white/10 bg-white/5 text-qace-muted hover:bg-white/10 hover:text-white"
                      }`}
                    >
                      <p className="font-semibold">{title}</p>
                    </button>
                  ))}
                </div>
              </section>

              <section className="mt-6">
                <p className="text-sm font-semibold text-white">2. How Many Questions?</p>
                <div className="mt-3 grid gap-2 md:grid-cols-4">
                  {[10, 20, 30, 50].map((count) => {
                    const active = selectedQuestionCount === count;
                    return (
                      <button
                        key={count}
                        onClick={() => setSelectedQuestionCount(count)}
                        className={`rounded-lg border px-3 py-3 text-center text-sm transition ${
                          active
                            ? "border-sky-300 bg-sky-500/20 text-white"
                            : "border-white/10 bg-white/5 text-qace-muted hover:bg-white/10 hover:text-white"
                        }`}
                      >
                        <p className="text-2xl font-semibold">{count}</p>
                        <p>
                          {count === 10
                            ? "Quick"
                            : count === 20
                              ? "Standard"
                              : count === 30
                                ? "Extended"
                                : "Intensive"}
                        </p>
                      </button>
                    );
                  })}
                </div>
              </section>

              <section className="mt-6">
                <p className="text-sm font-semibold text-white">3. Difficulty</p>
                <div className="mt-3 grid gap-2 md:grid-cols-4">
                  {(["easy", "medium", "hard", "random"] as const).map((level) => (
                    <button
                      key={level}
                      onClick={() => setSelectedDifficulty(level)}
                      className={`rounded-lg border px-3 py-3 text-left text-sm transition ${
                        selectedDifficulty === level
                          ? "border-sky-300 bg-sky-500/20 text-white"
                          : "border-white/10 bg-white/5 text-qace-muted hover:bg-white/10 hover:text-white"
                      }`}
                    >
                      <p className="font-semibold capitalize">{level}</p>
                    </button>
                  ))}
                </div>
              </section>

              <section className="mt-6">
                <p className="text-sm font-semibold text-white">4. When to See Answers?</p>
                <div className="mt-3 grid gap-2 md:grid-cols-2">
                  <button
                    onClick={() => setSelectedAnswerMode("each")}
                    className={`rounded-lg border px-3 py-3 text-left text-sm transition ${
                      selectedAnswerMode === "each"
                        ? "border-sky-300 bg-sky-500/20 text-white"
                        : "border-white/10 bg-white/5 text-qace-muted hover:bg-white/10 hover:text-white"
                    }`}
                  >
                    <p className="font-semibold">After Each Question</p>
                    <p className="text-xs text-qace-muted">See explanation immediately</p>
                  </button>
                  <button
                    onClick={() => setSelectedAnswerMode("end")}
                    className={`rounded-lg border px-3 py-3 text-left text-sm transition ${
                      selectedAnswerMode === "end"
                        ? "border-sky-300 bg-sky-500/20 text-white"
                        : "border-white/10 bg-white/5 text-qace-muted hover:bg-white/10 hover:text-white"
                    }`}
                  >
                    <p className="font-semibold">At the End</p>
                    <p className="text-xs text-qace-muted">Review all answers together</p>
                  </button>
                </div>
              </section>

              <section className="mt-6">
                <p className="text-sm font-semibold text-white">5. Time Limit</p>
                <div className="mt-3 grid gap-2 md:grid-cols-3">
                  <button
                    onClick={() => setSelectedTimeMode("per-question")}
                    className={`rounded-lg border px-3 py-3 text-left text-sm transition ${
                      selectedTimeMode === "per-question"
                        ? "border-sky-300 bg-sky-500/20 text-white"
                        : "border-white/10 bg-white/5 text-qace-muted hover:bg-white/10 hover:text-white"
                    }`}
                  >
                    <p className="font-semibold">Per Question</p>
                    <p className="text-xs text-qace-muted">20s each</p>
                  </button>
                  <button
                    onClick={() => setSelectedTimeMode("total")}
                    className={`rounded-lg border px-3 py-3 text-left text-sm transition ${
                      selectedTimeMode === "total"
                        ? "border-sky-300 bg-sky-500/20 text-white"
                        : "border-white/10 bg-white/5 text-qace-muted hover:bg-white/10 hover:text-white"
                    }`}
                  >
                    <p className="font-semibold">Total Time</p>
                    <p className="text-xs text-qace-muted">{Math.floor(selectedQuestionCount * 20 / 60)}m {(selectedQuestionCount * 20) % 60}s</p>
                  </button>
                  <button
                    onClick={() => setSelectedTimeMode("unlimited")}
                    className={`rounded-lg border px-3 py-3 text-left text-sm transition ${
                      selectedTimeMode === "unlimited"
                        ? "border-sky-300 bg-sky-500/20 text-white"
                        : "border-white/10 bg-white/5 text-qace-muted hover:bg-white/10 hover:text-white"
                    }`}
                  >
                    <p className="font-semibold">Unlimited</p>
                    <p className="text-xs text-qace-muted">No time pressure</p>
                  </button>
                </div>
              </section>

              <section className="mt-6 rounded-xl border border-white/10 bg-white/5 p-4">
                <div className="flex flex-wrap gap-2 text-xs text-qace-muted">
                  <span className="rounded-full border border-white/15 px-2 py-1">{selectedCatalogTopic.title}</span>
                  <span className="rounded-full border border-white/15 px-2 py-1">{selectedSubtopic}</span>
                  <span className="rounded-full border border-white/15 px-2 py-1">{selectedDifficulty}</span>
                  <span className="rounded-full border border-white/15 px-2 py-1">{selectedQuestionCount} questions</span>
                  <span className="rounded-full border border-white/15 px-2 py-1">{selectedAnswerMode === "end" ? "Review at end" : "Review each"}</span>
                  <span className="rounded-full border border-white/15 px-2 py-1">{selectedTimeMode === "unlimited" ? "Unlimited time" : selectedTimeMode}</span>
                </div>
                <button
                  onClick={async () => {
                    const isMixed = selectedCatalogTopic.id === MIXED_TOPIC_ID;
                    const dbQuestions = await fetchQuizQuestions({
                      topicId: isMixed ? "" : selectedCatalogTopic.id,
                      subtopic: isMixed ? "All Topics" : selectedSubtopic,
                      difficulty: selectedDifficulty,
                      count: selectedQuestionCount,
                      mixAcrossTopics: isMixed,
                    });

                    if (dbQuestions.length === 0) {
                      const localCount = isMixed ? 0 : getQuestionsForTopic(selectedCatalogTopic.id).length;
                      if (localCount === 0) {
                        setQuizConfigNotice("No questions found for this selection. Import mcq_questions into Supabase and try again.");
                        return;
                      }
                      setActiveTopicId(selectedCatalogTopic.id);
                      setLiveQuestions([]);
                    } else {
                      setActiveTopicId(selectedCatalogTopic.id === MIXED_TOPIC_ID ? "mixed-topics" : selectedCatalogTopic.id);
                      setLiveQuestions(dbQuestions);
                    }

                    setQuizState("running");
                    setCurrentIndex(0);
                    setAnswers({});
                    setStartedAt(new Date().toISOString());
                    setQuizConfigNotice("");
                  }}
                  className="mt-4 w-full rounded-lg bg-qace-primary px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-400"
                >
                  Start Quiz
                </button>
                {quizConfigNotice ? <p className="mt-2 text-xs text-amber-200">{quizConfigNotice}</p> : null}
              </section>
            </GlassCard>
          ) : null}
        </>
      ) : null}



      {mode === "study" ? (
        <div className="flex flex-col" style={{ minHeight: "70vh" }}>
          {/* Folder (topic) pill bar */}
          <div className="bg-gray-800/60 backdrop-blur-sm border border-gray-700/40 rounded-2xl px-4 py-3 grid grid-cols-5 gap-2 mb-4">
            {bucketTopicsLoading
              ? [...Array(10)].map((_, i) => <div key={i} className="h-9 bg-gray-700 rounded-lg animate-pulse" />)
              : bucketTopics.length === 0
              ? <p className="text-gray-500 text-sm col-span-5 text-center">No notes available.</p>
              : bucketTopics.map((t) => (
                  <button
                    key={t.folder}
                    onClick={() => void handleSelectFolder(t.folder)}
                    className={`h-9 rounded-lg text-xs font-medium text-center transition-all px-2 leading-tight ${
                      selectedFolder === t.folder
                        ? "bg-blue-600 text-white shadow-lg shadow-blue-600/30"
                        : "text-gray-400 hover:text-gray-200 hover:bg-gray-700/60 bg-gray-700/30"
                    }`}
                  >{t.label}</button>
                ))}
          </div>

          {/* Sidebar + content */}
          {folderFilesLoading ? (
            <div className="flex justify-center items-center h-64">
              <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : folderFiles.length > 0 ? (
            <div className="flex gap-4 items-start flex-1 min-h-0">
              {/* Sub-topic sidebar — each file in the folder */}
              <div className="w-56 shrink-0 sticky top-4">
                <div className="bg-gray-800/60 backdrop-blur-sm border border-gray-700/40 rounded-2xl overflow-hidden">
                  <div className="px-4 py-3 border-b border-gray-700/50">
                    <h3 className="text-gray-300 font-semibold text-xs uppercase tracking-widest">Sub-Topics</h3>
                  </div>
                  <nav className="py-1">
                    {folderFiles.map((f, idx) => (
                      <button
                        key={f.path}
                        onClick={() => void handleSelectStudyTopic(f.path)}
                        className={`w-full text-left px-4 py-2.5 text-sm transition-all border-l-2 ${
                          selectedStudyTopic === f.path
                            ? "bg-blue-600/20 text-blue-400 font-semibold border-blue-500"
                            : "text-gray-400 hover:text-gray-200 hover:bg-gray-700/40 border-transparent"
                        }`}
                      >
                        {f.label}
                      </button>
                    ))}
                  </nav>
                </div>
              </div>

              {/* Note content */}
              <div className="flex-1 min-w-0 flex flex-col gap-4">
                {selectedStudyTopic && loadingNotes[selectedStudyTopic] ? (
                  <div className="flex justify-center items-center h-64">
                    <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  </div>
                ) : selectedStudyTopic && notes[selectedStudyTopic] ? (
                  <>
                    <div className="bg-white text-gray-900 rounded-2xl shadow-2xl px-10 py-8">
                      <h2 className="text-2xl font-extrabold text-blue-700 mb-6 pb-3 border-b-2 border-blue-100 tracking-tight">
                        {folderFiles.find((f) => f.path === selectedStudyTopic)?.label ?? ""}
                      </h2>
                      <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
                        {preprocessNoteContent(notes[selectedStudyTopic])}
                      </ReactMarkdown>
                    </div>
                    {/* Prev / Next navigation */}
                    <div className="flex justify-between">
                      <button
                        disabled={folderFiles.findIndex((f) => f.path === selectedStudyTopic) === 0}
                        onClick={() => {
                          const idx = folderFiles.findIndex((f) => f.path === selectedStudyTopic);
                          if (idx > 0) void handleSelectStudyTopic(folderFiles[idx - 1].path);
                        }}
                        className="px-4 py-2 rounded-full bg-gray-800/60 border border-gray-700/40 text-gray-300 text-sm font-medium disabled:opacity-30 hover:bg-gray-700/60 transition-all"
                      >
                        ← Previous
                      </button>
                      <span className="text-gray-500 text-sm self-center">
                        {folderFiles.findIndex((f) => f.path === selectedStudyTopic) + 1} / {folderFiles.length}
                      </span>
                      <button
                        disabled={folderFiles.findIndex((f) => f.path === selectedStudyTopic) === folderFiles.length - 1}
                        onClick={() => {
                          const idx = folderFiles.findIndex((f) => f.path === selectedStudyTopic);
                          if (idx < folderFiles.length - 1) void handleSelectStudyTopic(folderFiles[idx + 1].path);
                        }}
                        className="px-4 py-2 rounded-full bg-gray-800/60 border border-gray-700/40 text-gray-300 text-sm font-medium disabled:opacity-30 hover:bg-gray-700/60 transition-all"
                      >
                        Next →
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="flex flex-col items-center justify-center h-64 text-center gap-3">
                    <p className="text-gray-400 text-lg">Select a sub-topic from the sidebar.</p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-64 text-center gap-3">
              <p className="text-gray-400 text-lg">Select a topic above to start studying.</p>
            </div>
          )}
        </div>
      ) : null}

      {mode === "quiz" && quizState === "running" && currentQuestion ? (
        <section className="grid gap-4 lg:grid-cols-[2fr_1fr]">
          <GlassCard className="animate-fade-up">
            <div className="flex items-center justify-between">
              <Badge>{`Question ${currentIndex + 1} / ${questions.length}`}</Badge>
              <span className="text-xs text-qace-muted">Topic: {activeTopicId}</span>
            </div>
            <h2 className="mt-4 text-xl font-semibold">{cleanQuestionPrompt(currentQuestion.prompt)}</h2>

            <div className="mt-5 space-y-2">
              {currentQuestion.options.map((option) => {
                const active = selectedOptionId === option.id;
                return (
                  <button
                    key={option.id}
                    onClick={() => selectAnswer(currentQuestion.id, option.id)}
                    className={`w-full rounded-lg border px-4 py-3 text-left text-sm transition ${
                      active
                        ? "border-sky-300 bg-sky-500/20 text-white"
                        : "border-white/10 bg-white/5 text-qace-muted hover:bg-white/10 hover:text-white"
                    }`}
                  >
                    <span className="font-semibold">{option.id.toUpperCase()}.</span> {option.text}
                  </button>
                );
              })}
            </div>

            {selectedAnswerMode === "each" && selectedOptionId ? (
              <div
                className={`mt-4 rounded-xl border p-4 ${
                  selectedOptionId === currentQuestion.correctOptionId
                    ? "border-emerald-300/40 bg-emerald-500/10"
                    : "border-rose-300/40 bg-rose-500/10"
                }`}
              >
                <p
                  className={`text-sm font-semibold ${
                    selectedOptionId === currentQuestion.correctOptionId ? "text-emerald-300" : "text-rose-300"
                  }`}
                >
                  {selectedOptionId === currentQuestion.correctOptionId ? "✓ Correct" : "✕ Incorrect"}
                </p>
                {currentQuestion.explanation ? (
                  <p className="mt-2 text-sm text-qace-muted">{currentQuestion.explanation}</p>
                ) : null}
              </div>
            ) : null}

            <div className="mt-6 flex items-center gap-3">
              <button
                onClick={nextOrFinish}
                disabled={!selectedOptionId}
                className="rounded-lg bg-qace-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {currentIndex >= questions.length - 1 ? "Finish Quiz" : "Next Question"}
              </button>
              <button
                onClick={() => setQuizState("topic-selection")}
                className="rounded-lg bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/15"
              >
                Cancel
              </button>
            </div>
          </GlassCard>

          <GlassCard className="animate-fade-up-delayed">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-qace-muted">Session Progress</h3>
            <div className="mt-4 space-y-4">
              <ProgressRow
                label="Completion"
                value={completionPercent}
                hint={`${answeredCount} of ${questions.length} questions answered`}
              />
            </div>
          </GlassCard>
        </section>
      ) : null}

      {mode === "quiz" && quizState === "completed" && lastAttempt ? (
        <section className="grid gap-4 lg:grid-cols-[2fr_1fr]">
          <GlassCard className="animate-fade-up">
            <p className="text-xs uppercase tracking-wide text-qace-muted">Quiz Complete</p>
            <h2 className="mt-2 text-2xl font-semibold">Score: {lastAttempt.score_percent.toFixed(0)}%</h2>
            <p className="mt-2 text-sm text-qace-muted">
              Correct answers: {lastAttempt.correct_answers}/{lastAttempt.total_questions}
            </p>

            <div className="mt-5 rounded-xl border border-white/10 bg-white/5 p-4">
              <p className="text-sm font-semibold text-white">Feedback</p>
              <p className="mt-2 text-sm text-qace-muted">{lastAttempt.feedback_summary}</p>
            </div>

            <div className="mt-5 space-y-3">
              <p className="text-sm font-semibold text-white">Answer Review</p>
              {questions
                .map((question, index) => ({ question, index }))
                .map(({ question, index }) => {
                const selected = answers[question.id] ?? "";
                const isCorrect = selected === question.correctOptionId;

                return (
                  <div key={question.id} className="rounded-xl border border-white/10 bg-white/5 p-4">
                    <p className="text-xs uppercase tracking-wide text-qace-muted">Question {index + 1}</p>
                    <p className="mt-1 text-sm font-semibold text-white">{cleanQuestionPrompt(question.prompt)}</p>

                    <div className="mt-3 space-y-2">
                      {question.options.map((option) => {
                        const isSelected = selected === option.id;
                        const isCorrectOption = question.correctOptionId === option.id;

                        let optionClass = "border-white/10 bg-white/5 text-qace-muted";
                        if (isSelected && isCorrectOption) {
                          optionClass = "border-emerald-300 bg-emerald-500/20 text-emerald-100";
                        } else if (isSelected && !isCorrectOption) {
                          optionClass = "border-rose-300 bg-rose-500/20 text-rose-100";
                        } else if (!isSelected && isCorrectOption) {
                          optionClass = "border-emerald-300/70 bg-emerald-500/10 text-emerald-100";
                        }

                        return (
                          <div key={option.id} className={`rounded-lg border px-3 py-2 text-sm ${optionClass}`}>
                            <span className="font-semibold">{option.id.toUpperCase()}.</span> {option.text}
                            {isSelected && isCorrectOption ? <span className="ml-2 font-semibold">✓</span> : null}
                            {isSelected && !isCorrectOption ? <span className="ml-2 font-semibold">✕</span> : null}
                            {!isSelected && isCorrectOption ? <span className="ml-2 text-xs font-semibold">Correct Answer</span> : null}
                          </div>
                        );
                      })}
                    </div>

                    <p className={`mt-3 text-sm font-semibold ${isCorrect ? "text-emerald-300" : "text-rose-300"}`}>
                      {isCorrect ? "✓ Correct" : "✕ Incorrect"}
                    </p>
                    {!isCorrect && question.explanation ? (
                      <div className="mt-3 rounded-lg border border-emerald-300/30 bg-emerald-500/10 px-3 py-2">
                        <p className="text-xs font-semibold uppercase tracking-wide text-emerald-200">Why this is the right answer</p>
                        <p className="mt-1 text-sm text-emerald-100">{question.explanation}</p>
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>

            <div className="mt-5 flex flex-wrap gap-3">
              <button
                onClick={retakeTopic}
                className="rounded-lg bg-qace-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400"
              >
                Retake Topic
              </button>
              <button
                onClick={() => setQuizState("topic-selection")}
                className="rounded-lg bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/15"
              >
                Choose Another Topic
              </button>
            </div>
          </GlassCard>

          <GlassCard className="animate-fade-up-delayed">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-qace-muted">Recent Attempts</h3>
            <div className="mt-3 space-y-2">
              {recentAttempts.length === 0 ? (
                <p className="text-sm text-qace-muted">No attempts yet.</p>
              ) : (
                recentAttempts.map((attempt) => (
                  <div key={attempt.id} className="rounded-lg border border-white/10 bg-white/5 px-3 py-2">
                    <p className="text-xs uppercase tracking-wide text-qace-muted">{attempt.topic_id}</p>
                    <p className="text-sm font-semibold text-white">{attempt.score_percent.toFixed(0)}%</p>
                  </div>
                ))
              )}
            </div>
          </GlassCard>
        </section>
      ) : null}
    </AppShell>
  );
}
