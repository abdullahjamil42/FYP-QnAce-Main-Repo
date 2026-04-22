"use client";

import { useState, useEffect } from "react";
import { createClientComponentClient } from "@supabase/auth-helpers-nextjs";
import { type User } from "@supabase/supabase-js";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const supabase = createClientComponentClient();

const TOPICS = [
  "System Design",
  "Data Structures & Algorithms",
  "Behavioral Questions",
  "Cloud Computing (AWS/GCP/Azure)",
  "Containerization (Docker/Kubernetes)",
  "CI/CD & DevOps",
  "Databases (SQL/NoSQL)",
  "Networking",
  "Security",
  "Frontend Development",
];

type Note = {
  id: string;
  topic: string;
  notes_markdown: string;
  updated_at: string;
};

type TopicNote = {
  topic_id: string;
  title: string;
  category: string;
  content?: string;
};

export default function PreparePage() {
  const [user, setUser] = useState<User | null>(null);
  const [notes, setNotes] = useState<Record<string, Note>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [mode, setMode] = useState<"quiz" | "notes" | "study">("quiz");

  // Study Notes state
  const [topicNotes, setTopicNotes] = useState<TopicNote[]>([]);
  const [topicNotesLoading, setTopicNotesLoading] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedStudyTopic, setSelectedStudyTopic] = useState<string | null>(null);
  const [studyContent, setStudyContent] = useState<string | null>(null);
  const [studyContentLoading, setStudyContentLoading] = useState(false);

  useEffect(() => {
    const checkUser = async () => {
      const { data } = await supabase.auth.getUser();
      setUser(data.user);
      if (data.user) {
        fetchNotes(data.user.id);
      }
    };
    checkUser();
  }, []);

  // Fetch topic list when study mode is entered
  useEffect(() => {
    if (mode === "study" && topicNotes.length === 0) {
      fetchTopicList();
    }
  }, [mode]);

  const fetchTopicList = async () => {
    setTopicNotesLoading(true);
    const { data, error } = await supabase
      .from("topic_notes")
      .select("topic_id, title, category")
      .order("category")
      .order("title");

    if (error) {
      console.error("Error fetching topic notes list:", error);
    } else {
      setTopicNotes(data ?? []);
    }
    setTopicNotesLoading(false);
  };

  const fetchStudyContent = async (topicId: string) => {
    setSelectedStudyTopic(topicId);
    setStudyContent(null);
    setStudyContentLoading(true);

    const { data, error } = await supabase
      .from("topic_notes")
      .select("content")
      .eq("topic_id", topicId)
      .single();

    if (error) {
      console.error("Error fetching study content:", error);
    } else {
      setStudyContent(data?.content ?? null);
    }
    setStudyContentLoading(false);
  };

  const fetchNotes = async (userId: string) => {
    const { data, error } = await supabase
      .from("study_notes")
      .select("*")
      .eq("user_id", userId);

    if (error) {
      console.error("Error fetching notes:", error);
    } else {
      const notesMap = data.reduce((acc, note) => {
        acc[note.topic] = note;
        return acc;
      }, {} as Record<string, Note>);
      setNotes(notesMap);
    }
  };

  const generateNotes = async (topic: string) => {
    if (!user) {
      alert("You must be logged in to generate notes.");
      return;
    }

    setLoading((prev) => ({ ...prev, [topic]: true }));

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_QACE_API_URL}/preparation/generate-notes`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic }),
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      const { notes_markdown } = result;

      // Upsert into Supabase
      const { data, error } = await supabase
        .from("study_notes")
        .upsert(
          {
            user_id: user.id,
            topic: topic,
            notes_markdown: notes_markdown,
            updated_at: new Date().toISOString(),
          },
          { onConflict: "user_id, topic" }
        )
        .select()
        .single();

      if (error) {
        throw error;
      }

      setNotes((prev) => ({ ...prev, [topic]: data }));
      setSelectedTopic(topic);

    } catch (error) {
      console.error(`Error generating notes for ${topic}:`, error);
      alert(`Failed to generate notes for ${topic}. Check the console for details.`);
    } finally {
      setLoading((prev) => ({ ...prev, [topic]: false }));
    }
  };

  const categories = Array.from(
    new Set(topicNotes.map((t) => t.category).filter(Boolean))
  ).sort();
  const subtopics = selectedCategory
    ? topicNotes.filter((t) => t.category === selectedCategory)
    : [];

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white overflow-hidden">
      {/* Mode toggle */}
      <div className="flex justify-center pt-4 pb-3 shrink-0">
        <div className="bg-gray-800 rounded-full p-1 flex">
          <button onClick={() => setMode("quiz")} className={`px-6 py-2 rounded-full text-sm font-semibold transition-colors ${mode === "quiz" ? "bg-blue-600 text-white" : "bg-transparent text-gray-400 hover:bg-gray-700"}`}>Quiz Catalog</button>
          <button onClick={() => setMode("notes")} className={`px-6 py-2 rounded-full text-sm font-semibold transition-colors ${mode === "notes" ? "bg-blue-600 text-white" : "bg-transparent text-gray-400 hover:bg-gray-700"}`}>Notes Catalog</button>
          <button onClick={() => setMode("study")} className={`px-6 py-2 rounded-full text-sm font-semibold transition-colors ${mode === "study" ? "bg-blue-600 text-white" : "bg-transparent text-gray-400 hover:bg-gray-700"}`}>Study Notes</button>
        </div>
      </div>

      {mode === "study" ? (
        <div className="flex flex-col flex-1 overflow-hidden">
          {/* Topic categories top bar */}
          <div className="bg-gray-800 border-b border-gray-700 px-6 py-3 flex gap-2 overflow-x-auto shrink-0">
            {topicNotesLoading
              ? [...Array(5)].map((_, i) => <div key={i} className="h-8 w-32 bg-gray-700 rounded-full animate-pulse shrink-0" />)
              : categories.length === 0
              ? <p className="text-gray-500 text-sm self-center">No topics available.</p>
              : categories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => { setSelectedCategory(cat); setSelectedStudyTopic(null); setStudyContent(null); }}
                    className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors shrink-0 ${selectedCategory === cat ? "bg-blue-600 text-white" : "bg-gray-700 text-gray-300 hover:bg-gray-600"}`}
                  >{cat}</button>
                ))}
          </div>

          {/* Subtopics row */}
          {selectedCategory && (
            <div className="px-6 py-2.5 flex gap-2 overflow-x-auto shrink-0 bg-gray-900 border-b border-gray-700">
              {subtopics.map((t) => (
                <button
                  key={t.topic_id}
                  onClick={() => fetchStudyContent(t.topic_id)}
                  className={`px-4 py-1.5 rounded-lg text-sm whitespace-nowrap transition-colors shrink-0 border ${selectedStudyTopic === t.topic_id ? "bg-blue-500 text-white border-blue-500 font-semibold" : "bg-gray-800 text-gray-300 border-gray-600 hover:border-blue-400 hover:text-blue-300"}`}
                >{t.title}</button>
              ))}
            </div>
          )}

          {/* PDF content area */}
          <div className="flex-1 overflow-y-auto p-8">
            {studyContentLoading ? (
              <div className="flex justify-center items-center h-64">
                <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : studyContent ? (
              <div className="max-w-4xl mx-auto">
                <div className="bg-white text-gray-900 rounded-2xl shadow-2xl px-16 py-12">
                  <article className="prose prose-slate max-w-none prose-headings:font-bold prose-headings:text-gray-900 prose-h1:text-3xl prose-h1:pb-3 prose-h1:mb-6 prose-h1:border-b prose-h1:border-gray-200 prose-h2:text-2xl prose-h2:mt-8 prose-h3:text-lg prose-h3:text-blue-700 prose-p:text-gray-700 prose-p:leading-relaxed prose-li:text-gray-700 prose-strong:text-gray-900 prose-code:bg-gray-100 prose-code:text-blue-700 prose-code:rounded prose-code:text-sm prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-pre:rounded-xl prose-blockquote:border-blue-400 prose-blockquote:text-gray-500">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{studyContent}</ReactMarkdown>
                  </article>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center gap-3">
                {!selectedCategory
                  ? <p className="text-gray-400 text-lg">Select a topic from the top bar to get started.</p>
                  : !selectedStudyTopic
                  ? <p className="text-gray-400 text-lg">Choose a subtopic to open its notes.</p>
                  : <p className="text-gray-500">Failed to load content. Please try again.</p>}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="flex flex-1 overflow-hidden">
          <aside className="w-64 bg-gray-800 p-4 overflow-y-auto shrink-0">
            <h1 className="text-xl font-bold mb-4">Preparation Topics</h1>
            <ul>
              {TOPICS.map((topic) => (
                <li key={topic} className="mb-2">
                  <div className="flex justify-between items-center">
                    <button
                      onClick={() => setSelectedTopic(topic)}
                      className={`text-left w-full text-sm hover:text-blue-400 ${
                        selectedTopic === topic ? "text-blue-500" : "text-gray-300"
                      }`}
                    >
                      {topic}
                    </button>
                    <button
                      onClick={() => generateNotes(topic)}
                      disabled={loading[topic]}
                      className="ml-2 px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 rounded disabled:bg-gray-500 shrink-0"
                    >
                      {loading[topic] ? "..." : "Gen"}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </aside>

          <main className="flex-1 p-6 overflow-y-auto">
            {mode === "notes" ? (
              selectedTopic && notes[selectedTopic] ? (
                <article className="prose prose-invert max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {notes[selectedTopic].notes_markdown}
                  </ReactMarkdown>
                </article>
              ) : (
                <div className="flex items-center justify-center h-full">
                  <p className="text-gray-400">
                    {selectedTopic
                      ? `Click "Gen" to create notes for ${selectedTopic}.`
                      : "Select a topic to view or generate notes."}
                  </p>
                </div>
              )
            ) : (
              <div className="text-center text-gray-400">
                <p>Quiz component will be here.</p>
              </div>
            )}
          </main>
        </div>
      )}
    </div>
  );
}
