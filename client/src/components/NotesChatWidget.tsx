"use client";

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { streamNotesChat, type NotesChatMessage } from "@/lib/backend";

type Props = {
  topic: string | null;
  section: string | null;
  noteContext: string;
  resetKey: string;
};

function renderInline(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <span key={i} className="font-semibold text-white">
        {part.slice(2, -2)}
      </span>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

function renderMessageContent(content: string) {
  if (!content) return null;
  return content.split("\n").map((line, i) => (
    <p key={i} className={i === 0 ? "" : "mt-1"}>
      {renderInline(line)}
    </p>
  ));
}

export default function NotesChatWidget({ topic, section, noteContext, resetKey }: Props) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<NotesChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const disabled = !topic || !noteContext.trim();

  useEffect(() => {
    setMessages([]);
    setInput("");
  }, [resetKey]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, open]);

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || streaming || disabled || !topic) return;

    const historyForRequest = messages.slice(-6);
    const newUserMessage: NotesChatMessage = { role: "user", content: trimmed };

    setMessages((prev) => [...prev, newUserMessage, { role: "assistant", content: "" }]);
    setInput("");
    setStreaming(true);

    try {
      const gen = streamNotesChat({
        topic,
        section: section ?? "",
        note_context: noteContext,
        history: historyForRequest,
        message: trimmed,
      });
      for await (const chunk of gen) {
        setMessages((prev) => {
          const next = prev.slice();
          const last = next[next.length - 1];
          if (last && last.role === "assistant") {
            next[next.length - 1] = { ...last, content: last.content + chunk };
          }
          return next;
        });
      }
    } catch (err) {
      const detail = err instanceof Error ? err.message : "unknown error";
      setMessages((prev) => {
        const next = prev.slice();
        const last = next[next.length - 1];
        if (last && last.role === "assistant") {
          next[next.length - 1] = {
            role: "assistant",
            content: `Sorry — I couldn't reach the assistant. ${detail}`,
          };
        }
        return next;
      });
    } finally {
      setStreaming(false);
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void sendMessage();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void sendMessage();
    }
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        disabled={disabled}
        title={disabled ? "Open a note to chat" : "Ask about this section"}
        className="fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-qace-primary text-white shadow-xl shadow-black/40 transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-40"
        aria-label="Open Notes Chat"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-6 w-6"
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </button>
    );
  }

  const subtitle = [topic, section].filter(Boolean).join(" — ");

  return (
    <div
      className="card-glow fixed bottom-6 right-6 z-40 flex h-[520px] w-[380px] flex-col overflow-hidden rounded-2xl border border-white/20 bg-white/5 shadow-xl shadow-black/40 backdrop-blur-md"
      role="dialog"
      aria-label="Notes Chat"
    >
      <div className="flex items-start justify-between border-b border-white/10 px-4 py-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-white">Notes Chat</p>
          {subtitle && (
            <p className="mt-0.5 truncate text-xs text-qace-muted" title={subtitle}>
              {subtitle}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="ml-2 rounded-md p-1 text-qace-muted transition hover:bg-white/10 hover:text-white"
          aria-label="Close Notes Chat"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-4 w-4"
          >
            <path d="M18 6 6 18" />
            <path d="m6 6 12 12" />
          </svg>
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-3 text-sm leading-relaxed">
        {messages.length === 0 ? (
          <p className="text-qace-muted">Ask anything about this section.</p>
        ) : (
          messages.map((m, idx) => {
            const isUser = m.role === "user";
            const isLastAssistant =
              !isUser && idx === messages.length - 1 && streaming && !m.content;
            return (
              <div key={idx} className={isUser ? "flex justify-end" : "flex justify-start"}>
                <div
                  className={
                    isUser
                      ? "max-w-[85%] rounded-xl bg-qace-primary px-3 py-2 text-white"
                      : "max-w-[85%] rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-qace-muted"
                  }
                >
                  {isLastAssistant ? (
                    <span className="inline-flex items-center gap-1">
                      <span className="h-2 w-2 animate-pulse rounded-full bg-qace-accent" />
                      <span className="text-xs">thinking…</span>
                    </span>
                  ) : (
                    renderMessageContent(m.content)
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      <form onSubmit={onSubmit} className="flex gap-2 border-t border-white/10 p-3">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          placeholder="Ask about this section…"
          className="flex-1 resize-none rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-white placeholder:text-qace-muted focus:border-qace-primary focus:outline-none"
          disabled={streaming}
        />
        <button
          type="submit"
          disabled={streaming || !input.trim() || disabled}
          className="rounded-lg bg-qace-primary px-3 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
