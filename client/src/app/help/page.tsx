import AppShell from "@/components/AppShell";
import { GlassCard } from "@/components/ui";

const faqs = [
  {
    question: "Why is my live transcript delayed?",
    answer: "Check network stability and microphone clarity. High background noise can increase inference latency.",
  },
  {
    question: "How is my score calculated?",
    answer: "Final score combines content quality, delivery, and composure with weighted rubric logic.",
  },
  {
    question: "Can I retry the same interview mode?",
    answer: "Yes. Use Session Summary or Practice History pages to launch another run instantly.",
  },
];

export default function HelpPage() {
  return (
    <AppShell
      title="Help & FAQ"
      subtitle="Troubleshoot common issues and understand how Q&Ace evaluates your interview performance."
    >
      <section className="grid gap-4 md:grid-cols-2">
        {faqs.map((faq, index) => (
          <GlassCard key={faq.question} className={index === 0 ? "animate-fade-up" : index === 1 ? "animate-fade-up-delayed" : "animate-fade-up-delayed-2"}>
            <h2 className="text-lg font-semibold">{faq.question}</h2>
            <p className="mt-2 text-sm text-qace-muted">{faq.answer}</p>
          </GlassCard>
        ))}
      </section>

      <GlassCard className="mt-4 animate-fade-up-delayed-2">
        <h3 className="text-lg font-semibold">Need support?</h3>
        <p className="mt-2 text-sm text-qace-muted">For setup issues, check camera permissions, microphone input source, and backend service availability on port 8000.</p>
      </GlassCard>
    </AppShell>
  );
}
