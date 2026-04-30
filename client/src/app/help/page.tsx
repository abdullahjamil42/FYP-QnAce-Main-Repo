import AppShell from "@/components/AppShell";

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
      <div className="card-glow animate-fade-up overflow-hidden rounded-2xl border border-white/20 bg-white/5 shadow-xl shadow-black/40 backdrop-blur-md">
        {faqs.map((faq) => (
          <div key={faq.question} className="border-b border-white/10 px-5 py-5">
            <h2 className="text-lg font-semibold">{faq.question}</h2>
            <p className="mt-2 text-sm text-qace-muted">{faq.answer}</p>
          </div>
        ))}
        <div className="px-5 py-5">
          <h3 className="text-lg font-semibold">Need support?</h3>
          <p className="mt-2 text-sm text-qace-muted">For setup issues, check camera permissions, microphone input source, and backend service availability on port 8000.</p>
        </div>
      </div>
    </AppShell>
  );
}
