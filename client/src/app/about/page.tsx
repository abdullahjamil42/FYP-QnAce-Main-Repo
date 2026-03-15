import AppShell from "@/components/AppShell";
import { GlassCard } from "@/components/ui";

export default function AboutPage() {
  return (
    <AppShell
      title="About Q&Ace"
      subtitle="Q&Ace is an AI-powered interview preparation platform designed to improve confidence, clarity, and consistency through multimodal feedback."
    >
      <section className="grid gap-4 lg:grid-cols-3">
        <GlassCard className="animate-fade-up">
          <h2 className="text-lg font-semibold">Mission</h2>
          <p className="mt-2 text-sm text-qace-muted">
            Help candidates practice high-stakes interviews with realistic feedback loops they can trust.
          </p>
        </GlassCard>
        <GlassCard className="animate-fade-up-delayed">
          <h2 className="text-lg font-semibold">How It Works</h2>
          <p className="mt-2 text-sm text-qace-muted">
            Live conversation signals are analyzed across text, voice, and facial cues, then consolidated into coaching insights.
          </p>
        </GlassCard>
        <GlassCard className="animate-fade-up-delayed-2">
          <h2 className="text-lg font-semibold">Outcome</h2>
          <p className="mt-2 text-sm text-qace-muted">
            Candidates gain measurable progress over repeated sessions and know exactly what to improve next.
          </p>
        </GlassCard>
      </section>
    </AppShell>
  );
}
