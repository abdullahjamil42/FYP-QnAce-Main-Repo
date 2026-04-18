"use client";

import { useState, useEffect } from "react";
import { createClientComponentClient } from "@supabase/auth-helpers-nextjs";
import { type User } from "@supabase/supabase-js";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

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

export default function PreparePage() {
  const supabase = createClientComponentClient();
  const [user, setUser] = useState<User | null>(null);
  const [notes, setNotes] = useState<Record<string, Note>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [mode, setMode] = useState<"quiz" | "notes">("quiz");

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

  return (
    <div className="flex h-screen bg-gray-900 text-white">
      <aside className="w-1/4 bg-gray-800 p-4 overflow-y-auto">
        <h1 className="text-2xl font-bold mb-4">Preparation Topics</h1>
        <ul>
          {TOPICS.map((topic) => (
            <li key={topic} className="mb-2">
              <div className="flex justify-between items-center">
                <button
                  onClick={() => setSelectedTopic(topic)}
                  className={`text-left w-full hover:text-blue-400 ${selectedTopic === topic ? 'text-blue-500' : ''}`}
                >
                  {topic}
                </button>
                <button
                  onClick={() => generateNotes(topic)}
                  disabled={loading[topic]}
                  className="ml-2 px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 rounded disabled:bg-gray-500"
                >
                  {loading[topic] ? "..." : "Generate"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      </aside>
      <main className="w-3/4 p-6 overflow-y-auto">
        <div className="flex justify-center mb-8">
          <div className="bg-gray-800 rounded-full p-1 flex">
            <button
              onClick={() => setMode("quiz")}
              className={`px-6 py-2 rounded-full text-sm font-semibold ${
                mode === "quiz"
                  ? "bg-blue-600 text-white"
                  : "bg-transparent text-gray-400 hover:bg-gray-700"
              }`}
            >
              Quiz Catalog
            </button>
            <button
              onClick={() => setMode("notes")}
              className={`px-6 py-2 rounded-full text-sm font-semibold ${
                mode === "notes"
                  ? "bg-blue-600 text-white"
                  : "bg-transparent text-gray-400 hover:bg-gray-700"
              }`}
            >
              Notes Catalog
            </button>
          </div>
        </div>

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
                  ? `Click "Generate" to create notes for ${selectedTopic}.`
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
  );
}
