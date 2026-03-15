import Link from "next/link";
import AppShell from "@/components/AppShell";
import { GlassCard } from "@/components/ui";

const drills = [
  {
    title: "Technical Deep Dive",
    duration: "8 min",
    prompt: "Explain a recent architecture decision and trade-offs.",
  },
  {
    title: "Behavioral STAR Sprint",
    duration: "6 min",
    prompt: "Describe a high-pressure conflict and how you resolved it.",
  },
  {
    title: "Leadership Reflection",
    duration: "9 min",
    prompt: "How did you influence a team without direct authority?",
  },
];

export default function PracticePage() {
  return (
    <AppShell
      title="Question Bank & Practice"
      subtitle="Run quick drills between full sessions to sharpen weak categories and improve confidence faster."
      actions={
        <Link href="/session/live" className="rounded-full bg-qace-primary px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400">
          Start Full Mock
        </Link>
      }
    >
      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {drills.map((drill, index) => (
          <GlassCard key={drill.title} className={index === 0 ? "animate-fade-up" : index === 1 ? "animate-fade-up-delayed" : "animate-fade-up-delayed-2"}>
            <p className="text-xs uppercase tracking-wide text-qace-muted">{drill.duration}</p>
            <h2 className="mt-2 text-lg font-semibold">{drill.title}</h2>
            <p className="mt-3 text-sm text-qace-muted">{drill.prompt}</p>
            <button className="mt-4 rounded-lg bg-white/10 px-3 py-2 text-sm font-semibold transition hover:bg-white/15">Launch Drill</button>
          </GlassCard>
        ))}
      </section>
    </AppShell>
  );
}
