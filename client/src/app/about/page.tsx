import Link from "next/link";
import AppShell from "@/components/AppShell";

const pillars = [
  {
    title: "Mission",
    text: "Help candidates practice high-stakes interviews with realistic feedback loops they can trust — anywhere, any time, without paying for a human coach.",
  },
  {
    title: "How It Works",
    text: "Live conversation signals are analysed across text, voice, and facial cues, then consolidated into a single coaching report you can act on.",
  },
  {
    title: "Outcome",
    text: "Candidates gain measurable progress over repeated sessions and know exactly what to improve next — confidence, clarity, content, or composure.",
  },
];

const features = [
  {
    title: "Behavioural Mock Interviews",
    text: "Conversational AI interviewer trained on common BHV question patterns. Answers are scored on STAR structure, clarity, and impact.",
  },
  {
    title: "Technical Q&A",
    text: "Topic-targeted question generation backed by a fine-tuned Llama model, with depth-aware follow-ups and a per-question scoring rubric.",
  },
  {
    title: "Coding Round (DSA)",
    text: "Browser-based code editor with curated DSA problems, run-on-the-fly evaluation, and an AI reviewer that explains where your solution fell short.",
  },
  {
    title: "Multimodal Feedback",
    text: "Voice tone, pacing, and facial composure are tracked alongside transcript quality so you see the full delivery picture, not just the words.",
  },
  {
    title: "Personalised Reports",
    text: "Every session produces a downloadable report with strengths, weaknesses, transcript highlights, and concrete drills for next time.",
  },
  {
    title: "Progress History",
    text: "All sessions are saved to your profile so you can compare runs, watch trends, and prove improvement over weeks of practice.",
  },
];

const techStack = [
  { label: "Frontend", value: "Next.js 14 · TypeScript · Tailwind" },
  { label: "Backend", value: "FastAPI · Python · WebSockets" },
  { label: "Auth & DB", value: "Supabase (Postgres + Storage)" },
  { label: "LLMs", value: "Llama 3 · fine-tuned LoRA · Ollama" },
  { label: "Speech", value: "Whisper STT · Coqui-style TTS" },
  { label: "Vision", value: "MediaPipe FaceMesh" },
];

const team = [
  { role: "Frontend & UX", name: "Abdullah Jamil" },
  { role: "ML & AI", name: "Muhammad Aziq Rauf" },
  { role: "Backend", name: "Shamil Sajjad" },
];

export default function AboutPage() {
  return (
    <AppShell
      title="About Q&Ace"
      subtitle="Q&Ace is an AI-powered interview preparation platform built to make high-quality mock interviews accessible to every candidate, on every device, at any hour."
    >
      {/* Story */}
      <section className="card-glow animate-fade-up mb-6 rounded-2xl border border-white/20 bg-white/5 p-5 shadow-xl shadow-black/30 backdrop-blur-md sm:p-7">
        <h2 className="text-xl font-semibold text-white sm:text-2xl">Why we built it</h2>
        <p className="mt-3 text-sm text-qace-muted sm:text-base">
          Interview preparation is broken. Coaching sessions are expensive, peer
          mocks are inconsistent, and reading question banks does nothing for
          delivery. Q&amp;Ace closes that gap — a realistic AI interviewer that
          asks, listens, watches, and gives you feedback grounded in evidence
          from the conversation itself.
        </p>
        <p className="mt-3 text-sm text-qace-muted sm:text-base">
          The result is a focused practice loop: <span className="text-white">configure → interview → review → repeat</span>.
          Each loop sharpens a specific weakness, and your history shows the
          improvement over time.
        </p>
      </section>

      {/* Pillars */}
      <section className="animate-fade-up-delayed mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {pillars.map((p) => (
          <article
            key={p.title}
            className="card-glow rounded-2xl border border-white/20 bg-white/5 p-5 backdrop-blur-md"
          >
            <h3 className="text-base font-semibold text-white sm:text-lg">{p.title}</h3>
            <p className="mt-2 text-sm text-qace-muted">{p.text}</p>
          </article>
        ))}
      </section>

      {/* Features */}
      <section className="animate-fade-up-delayed-2 mb-6">
        <h2 className="mb-3 text-xl font-semibold text-white sm:text-2xl">What's inside</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {features.map((f) => (
            <article
              key={f.title}
              className="card-glow rounded-2xl border border-white/15 bg-white/5 p-5 backdrop-blur-md"
            >
              <h3 className="text-base font-semibold text-white sm:text-lg">{f.title}</h3>
              <p className="mt-2 text-sm text-qace-muted">{f.text}</p>
            </article>
          ))}
        </div>
      </section>

      {/* Tech */}
      <section className="animate-fade-up-delayed-2 mb-6">
        <h2 className="mb-3 text-xl font-semibold text-white sm:text-2xl">Built with</h2>
        <div className="card-glow rounded-2xl border border-white/15 bg-white/5 p-5 backdrop-blur-md sm:p-6">
          <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
            {techStack.map((t) => (
              <div key={t.label} className="flex flex-col gap-0.5 border-b border-white/10 pb-2 last:border-b-0 sm:border-b-0 sm:pb-0">
                <dt className="text-xs font-semibold uppercase tracking-[0.18em] text-white/60">
                  {t.label}
                </dt>
                <dd className="text-sm text-white">{t.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* Team */}
      <section className="animate-fade-up-delayed-2 mb-6">
        <h2 className="mb-3 text-xl font-semibold text-white sm:text-2xl">The team</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {team.map((member) => (
            <article
              key={member.role}
              className="card-glow rounded-2xl border border-white/15 bg-white/5 p-4 text-center backdrop-blur-md"
            >
              <p className="text-xs uppercase tracking-[0.18em] text-white/60">
                {member.role}
              </p>
              <p className="mt-1 text-sm font-semibold text-white">{member.name}</p>
            </article>
          ))}
        </div>
        <p className="mt-3 text-xs text-qace-muted">
          Q&amp;Ace is a Final Year Project. We are a small team of students focused on shipping a useful product, not a demo.
        </p>
      </section>

      {/* CTA */}
      <section className="animate-fade-up-delayed-2 card-glow rounded-3xl border border-white/25 bg-white/5 p-6 text-center sm:p-8">
        <p className="text-[11px] uppercase tracking-[0.2em] text-qace-muted sm:text-xs">
          Ready to try it?
        </p>
        <h2 className="mt-2 text-2xl font-semibold text-white sm:text-3xl">
          Start a mock interview in under a minute.
        </h2>
        <div className="mt-5 flex flex-col items-stretch justify-center gap-3 sm:flex-row sm:items-center">
          <Link
            href="/setup"
            className="rounded-full bg-qace-primary px-6 py-3 text-sm font-semibold text-white transition hover:bg-indigo-400"
          >
            Start a Session
          </Link>
          <Link
            href="/help"
            className="rounded-full border border-white/25 bg-white/10 px-6 py-3 text-sm font-semibold text-white transition hover:bg-white/15"
          >
            Read the Help Guide
          </Link>
        </div>
      </section>
    </AppShell>
  );
}
