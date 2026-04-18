export const jobRoles = [
  {
    id: "cloud_computing",
    title: "Cloud Computing",
    description: "AWS, Azure, GCP, infrastructure design, DevOps, and cloud-native architecture.",
    icon: "☁️",
  },
  {
    id: "ai_engineering",
    title: "AI Engineering",
    description: "Machine learning pipelines, model deployment, MLOps, and AI system design.",
    icon: "🤖",
  },
  {
    id: "data_scientist",
    title: "Data Scientist",
    description: "Statistical analysis, data modeling, feature engineering, and experiment design.",
    icon: "📊",
  },
  {
    id: "web_engineering",
    title: "Web Engineering",
    description: "Frontend frameworks, REST/GraphQL APIs, performance optimization, and responsive design.",
    icon: "🌐",
  },
  {
    id: "software_engineer",
    title: "Software Engineer",
    description: "Algorithms, system design, data structures, and full-stack development.",
    icon: "💻",
  },
];

export const interviewTypes = [
  {
    id: "quick",
    title: "Quick Interview",
    description: "10-minute sprint with 5–7 focused questions. Great for a fast warm-up.",
    durationMinutes: 10,
    questionCount: 7,
  },
  {
    id: "extensive",
    title: "Extensive Interview",
    description: "No time limit, ~15 harder questions. Full emotion and facial analysis enabled.",
    durationMinutes: 0,
    questionCount: 15,
  },
];

export const roundTypes = [
  {
    id: "verbal",
    title: "Verbal Interview",
    description: "Traditional Q&A with the AI interviewer covering behavioral and technical questions.",
    icon: "🎤",
  },
  {
    id: "coding",
    title: "Technical Coding",
    description: "Solve coding problems in a live editor with real-time evaluation, complexity analysis, and scoring.",
    icon: "🧑‍💻",
  },
];

export const summary = {
  overall: 82,
  role: "Backend Engineer",
  duration: "17m",
  strengths: [
    "Clear ownership in project stories",
    "Strong technical depth and examples",
    "Steady speaking pace under pressure",
  ],
  opportunities: [
    "Reduce filler words in long answers",
    "Add clearer impact metrics",
    "Hold eye contact longer during follow-up",
  ],
};

export const history = [
  { id: "sess-104", date: "2026-03-15", mode: "Technical", score: 84, status: "Improved" },
  { id: "sess-097", date: "2026-03-13", mode: "Behavioral", score: 79, status: "Stable" },
  { id: "sess-091", date: "2026-03-10", mode: "Leadership", score: 74, status: "Needs Focus" },
  { id: "sess-083", date: "2026-03-08", mode: "Technical", score: 81, status: "Improved" },
];

export const reportBreakdown = [
  { label: "Content Quality", value: 86 },
  { label: "Delivery", value: 79 },
  { label: "Composure", value: 81 },
  { label: "Vocal Confidence", value: 77 },
  { label: "Facial Engagement", value: 74 },
];
