import AppShell from "@/components/AppShell";

export default function AboutPage() {
  return (
    <AppShell
      title="About Q&Ace"
      subtitle="Q&Ace is an AI-powered interview preparation platform designed to improve confidence, clarity, and consistency through multimodal feedback."
    >
      <div className="card-glow animate-fade-up overflow-hidden rounded-2xl border border-white/20 bg-white/5 shadow-xl shadow-black/40 backdrop-blur-md">
        <div className="grid grid-cols-1 divide-y divide-white/10 lg:grid-cols-3 lg:divide-x lg:divide-y-0">
          <div className="px-5 py-5">
            <h2 className="text-lg font-semibold">Mission</h2>
            <p className="mt-2 text-sm text-qace-muted">
              Help candidates practice high-stakes interviews with realistic feedback loops they can trust.
            </p>
          </div>
          <div className="px-5 py-5">
            <h2 className="text-lg font-semibold">How It Works</h2>
            <p className="mt-2 text-sm text-qace-muted">
              Live conversation signals are analyzed across text, voice, and facial cues, then consolidated into coaching insights.
            </p>
          </div>
          <div className="px-5 py-5">
            <h2 className="text-lg font-semibold">Outcome</h2>
            <p className="mt-2 text-sm text-qace-muted">
              Candidates gain measurable progress over repeated sessions and know exactly what to improve next.
            </p>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
