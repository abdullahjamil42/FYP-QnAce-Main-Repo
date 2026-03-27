export type MCQOption = {
  id: string;
  text: string;
};

export type MCQQuestion = {
  id: string;
  topicId: string;
  prompt: string;
  options: MCQOption[];
  correctOptionId: string;
  explanation: string;
};

export type MCQTopic = {
  id: string;
  title: string;
  description: string;
};

export const mcqTopics: MCQTopic[] = [
  {
    id: "technical",
    title: "Technical Foundations",
    description: "Core software engineering concepts, architecture, and system behavior.",
  },
  {
    id: "behavioral",
    title: "Behavioral Scenarios",
    description: "Situational judgement and STAR-style communication decisions.",
  },
  {
    id: "leadership",
    title: "Leadership and Ownership",
    description: "Influence, prioritization, delegation, and delivery under constraints.",
  },
];

export const mcqQuestions: MCQQuestion[] = [
  {
    id: "tech-1",
    topicId: "technical",
    prompt: "Which API design choice most reduces accidental breaking changes for consumers?",
    options: [
      { id: "a", text: "Use positional arguments for all required fields" },
      { id: "b", text: "Version endpoints and keep backward compatibility contracts" },
      { id: "c", text: "Return plain text errors only" },
      { id: "d", text: "Disable schema validation in production" },
    ],
    correctOptionId: "b",
    explanation: "Versioning plus compatibility policy allows incremental evolution without silently breaking clients.",
  },
  {
    id: "tech-2",
    topicId: "technical",
    prompt: "What is the strongest reason to add observability (logs, traces, metrics) early in a service?",
    options: [
      { id: "a", text: "It makes code compile faster" },
      { id: "b", text: "It eliminates all runtime failures" },
      { id: "c", text: "It shortens mean time to detect and resolve incidents" },
      { id: "d", text: "It replaces the need for tests" },
    ],
    correctOptionId: "c",
    explanation: "Observability improves incident response speed by showing where, when, and why failures happen.",
  },
  {
    id: "tech-3",
    topicId: "technical",
    prompt: "In a low-latency path, which optimization should be attempted first?",
    options: [
      { id: "a", text: "Rewrite everything in a different language" },
      { id: "b", text: "Measure bottlenecks with profiling before changing architecture" },
      { id: "c", text: "Increase retry count aggressively" },
      { id: "d", text: "Disable input validation" },
    ],
    correctOptionId: "b",
    explanation: "Profile-first optimization prevents wasted effort and regressions caused by premature changes.",
  },
  {
    id: "tech-4",
    topicId: "technical",
    prompt: "What trade-off is most typical when choosing eventual consistency over strong consistency?",
    options: [
      { id: "a", text: "Lower availability and lower partition tolerance" },
      { id: "b", text: "Higher write latency with no scalability gains" },
      { id: "c", text: "Better scalability/availability with temporary stale reads" },
      { id: "d", text: "No trade-off, both behave the same" },
    ],
    correctOptionId: "c",
    explanation: "Eventual consistency often improves scale and resilience while allowing short windows of stale data.",
  },
  {
    id: "beh-1",
    topicId: "behavioral",
    prompt: "In STAR responses, which element demonstrates impact most clearly?",
    options: [
      { id: "a", text: "A detailed company history" },
      { id: "b", text: "A list of tools used" },
      { id: "c", text: "A quantified result linked to your action" },
      { id: "d", text: "A generic statement about teamwork" },
    ],
    correctOptionId: "c",
    explanation: "Interviewers evaluate outcomes. Quantified results tied to your action show effectiveness.",
  },
  {
    id: "beh-2",
    topicId: "behavioral",
    prompt: "A teammate misses deadlines repeatedly. What is the best first action?",
    options: [
      { id: "a", text: "Escalate publicly in the team channel" },
      { id: "b", text: "Privately clarify blockers and align on a recovery plan" },
      { id: "c", text: "Take over all of their tasks permanently" },
      { id: "d", text: "Wait until performance review season" },
    ],
    correctOptionId: "b",
    explanation: "Private, empathetic alignment on blockers and concrete next steps is constructive and scalable.",
  },
  {
    id: "beh-3",
    topicId: "behavioral",
    prompt: "When answering a failure question, what approach is strongest?",
    options: [
      { id: "a", text: "Blame external constraints only" },
      { id: "b", text: "Admit fault, show corrective actions, and share measurable learning" },
      { id: "c", text: "Avoid specifics to reduce risk" },
      { id: "d", text: "Claim there were no failures" },
    ],
    correctOptionId: "b",
    explanation: "Ownership plus concrete learning indicates maturity and repeatable growth.",
  },
  {
    id: "beh-4",
    topicId: "behavioral",
    prompt: "What makes a conflict-resolution story interview-ready?",
    options: [
      { id: "a", text: "Focusing mostly on the other person being wrong" },
      { id: "b", text: "Describing emotional details without resolution" },
      { id: "c", text: "Showing active listening, alignment, and measurable team outcome" },
      { id: "d", text: "Keeping the story under one sentence" },
    ],
    correctOptionId: "c",
    explanation: "Strong answers show process and outcomes, not just tension.",
  },
  {
    id: "lead-1",
    topicId: "leadership",
    prompt: "You have two high-priority requests and one team. What should you do first?",
    options: [
      { id: "a", text: "Pick the request from the loudest stakeholder" },
      { id: "b", text: "Delay both until next sprint" },
      { id: "c", text: "Align on business impact, urgency, and risk with stakeholders" },
      { id: "d", text: "Randomly choose one to avoid bias" },
    ],
    correctOptionId: "c",
    explanation: "Transparent prioritization on impact and risk builds trust and improves decision quality.",
  },
  {
    id: "lead-2",
    topicId: "leadership",
    prompt: "What is a sign of healthy delegation?",
    options: [
      { id: "a", text: "Delegating without context to save time" },
      { id: "b", text: "Delegating outcome ownership with clarity, support, and check-ins" },
      { id: "c", text: "Delegating only low-impact tasks" },
      { id: "d", text: "Keeping decision rights only with manager" },
    ],
    correctOptionId: "b",
    explanation: "Delegation works when goals, boundaries, and support are clear.",
  },
  {
    id: "lead-3",
    topicId: "leadership",
    prompt: "How should you communicate a delayed delivery to stakeholders?",
    options: [
      { id: "a", text: "Share late only after a final date is guaranteed" },
      { id: "b", text: "Communicate early with impact, options, and mitigation plan" },
      { id: "c", text: "Only update your direct manager" },
      { id: "d", text: "Avoid discussing root cause" },
    ],
    correctOptionId: "b",
    explanation: "Early transparency plus options allows stakeholders to make informed trade-offs.",
  },
  {
    id: "lead-4",
    topicId: "leadership",
    prompt: "A junior teammate asks for help frequently. What is the best leadership response?",
    options: [
      { id: "a", text: "Provide direct answers every time" },
      { id: "b", text: "Ignore requests to force independence" },
      { id: "c", text: "Coach with frameworks and gradually increase autonomy" },
      { id: "d", text: "Reassign them off the project" },
    ],
    correctOptionId: "c",
    explanation: "Coaching builds durable capability while maintaining delivery momentum.",
  },
];

export function getQuestionsForTopic(topicId: string) {
  return mcqQuestions.filter((question) => question.topicId === topicId);
}
