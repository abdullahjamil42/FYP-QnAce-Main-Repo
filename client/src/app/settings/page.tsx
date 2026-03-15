import AppShell from "@/components/AppShell";
import { GlassCard } from "@/components/ui";

export default function SettingsPage() {
  return (
    <AppShell
      title="Profile & Preferences"
      subtitle="Personalize your interview prep defaults, feedback behavior, and privacy controls."
    >
      <section className="grid gap-4 md:grid-cols-2">
        <GlassCard className="animate-fade-up">
          <h2 className="text-lg font-semibold">Interview Defaults</h2>
          <div className="mt-4 space-y-3 text-sm text-qace-muted">
            <label className="flex items-center justify-between rounded-lg bg-black/20 px-3 py-2">
              <span>Default mode</span>
              <span className="text-white">Technical</span>
            </label>
            <label className="flex items-center justify-between rounded-lg bg-black/20 px-3 py-2">
              <span>Session length</span>
              <span className="text-white">20 minutes</span>
            </label>
            <label className="flex items-center justify-between rounded-lg bg-black/20 px-3 py-2">
              <span>Difficulty</span>
              <span className="text-white">Standard</span>
            </label>
          </div>
        </GlassCard>

        <GlassCard className="animate-fade-up-delayed">
          <h2 className="text-lg font-semibold">Device & Privacy</h2>
          <div className="mt-4 space-y-3 text-sm text-qace-muted">
            <label className="flex items-center justify-between rounded-lg bg-black/20 px-3 py-2">
              <span>Camera preview in lobby</span>
              <input type="checkbox" defaultChecked className="h-4 w-4 accent-qace-primary" />
            </label>
            <label className="flex items-center justify-between rounded-lg bg-black/20 px-3 py-2">
              <span>Store session transcripts</span>
              <input type="checkbox" defaultChecked className="h-4 w-4 accent-qace-primary" />
            </label>
            <label className="flex items-center justify-between rounded-lg bg-black/20 px-3 py-2">
              <span>Email performance digest</span>
              <input type="checkbox" className="h-4 w-4 accent-qace-primary" />
            </label>
          </div>
        </GlassCard>
      </section>
    </AppShell>
  );
}
