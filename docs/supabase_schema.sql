-- Q&Ace Supabase schema
-- Run in Supabase SQL editor.

create extension if not exists pgcrypto;

create table if not exists public.interview_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  mode text not null,
  difficulty text not null,
  duration_minutes integer not null default 20,
  status text not null default 'completed',
  started_at timestamptz not null,
  ended_at timestamptz not null,
  final_score numeric not null default 0,
  content_score numeric not null default 0,
  delivery_score numeric not null default 0,
  composure_score numeric not null default 0,
  transcript_events jsonb not null default '[]'::jsonb,
  latest_perception jsonb,
  webrtc_session_id text,
  created_at timestamptz not null default now()
);

create index if not exists interview_sessions_user_created_idx
  on public.interview_sessions (user_id, created_at desc);

alter table public.interview_sessions enable row level security;

drop policy if exists "Users can read own sessions" on public.interview_sessions;
create policy "Users can read own sessions"
  on public.interview_sessions
  for select
  using (auth.uid() = user_id);

drop policy if exists "Users can insert own sessions" on public.interview_sessions;
create policy "Users can insert own sessions"
  on public.interview_sessions
  for insert
  with check (auth.uid() = user_id);

drop policy if exists "Users can update own sessions" on public.interview_sessions;
create policy "Users can update own sessions"
  on public.interview_sessions
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "Users can delete own sessions" on public.interview_sessions;
create policy "Users can delete own sessions"
  on public.interview_sessions
  for delete
  using (auth.uid() = user_id);

create table if not exists public.mcq_attempts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  topic_id text not null,
  started_at timestamptz not null,
  completed_at timestamptz not null,
  total_questions integer not null,
  correct_answers integer not null,
  score_percent numeric not null,
  answers jsonb not null default '[]'::jsonb,
  feedback_summary text not null,
  created_at timestamptz not null default now()
);

create index if not exists mcq_attempts_user_created_idx
  on public.mcq_attempts (user_id, created_at desc);

create index if not exists mcq_attempts_user_topic_idx
  on public.mcq_attempts (user_id, topic_id, completed_at desc);

alter table public.mcq_attempts enable row level security;

drop policy if exists "Users can read own mcq attempts" on public.mcq_attempts;
create policy "Users can read own mcq attempts"
  on public.mcq_attempts
  for select
  using (auth.uid() = user_id);

drop policy if exists "Users can insert own mcq attempts" on public.mcq_attempts;
create policy "Users can insert own mcq attempts"
  on public.mcq_attempts
  for insert
  with check (auth.uid() = user_id);

drop policy if exists "Users can update own mcq attempts" on public.mcq_attempts;
create policy "Users can update own mcq attempts"
  on public.mcq_attempts
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "Users can delete own mcq attempts" on public.mcq_attempts;
create policy "Users can delete own mcq attempts"
  on public.mcq_attempts
  for delete
  using (auth.uid() = user_id);

create table if not exists public.mcq_topic_progress (
  user_id uuid not null references auth.users(id) on delete cascade,
  topic_id text not null,
  attempts_count integer not null default 0,
  best_score numeric not null default 0,
  average_score numeric not null default 0,
  latest_score numeric not null default 0,
  last_attempt_at timestamptz not null,
  updated_at timestamptz not null default now(),
  primary key (user_id, topic_id)
);

create index if not exists mcq_topic_progress_user_idx
  on public.mcq_topic_progress (user_id);

alter table public.mcq_topic_progress enable row level security;

drop policy if exists "Users can read own mcq progress" on public.mcq_topic_progress;
create policy "Users can read own mcq progress"
  on public.mcq_topic_progress
  for select
  using (auth.uid() = user_id);

drop policy if exists "Users can insert own mcq progress" on public.mcq_topic_progress;
create policy "Users can insert own mcq progress"
  on public.mcq_topic_progress
  for insert
  with check (auth.uid() = user_id);

drop policy if exists "Users can update own mcq progress" on public.mcq_topic_progress;
create policy "Users can update own mcq progress"
  on public.mcq_topic_progress
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "Users can delete own mcq progress" on public.mcq_topic_progress;
create policy "Users can delete own mcq progress"
  on public.mcq_topic_progress
  for delete
  using (auth.uid() = user_id);

create table if not exists public.mcq_topics (
  id text primary key,
  title text not null,
  description text,
  default_questions integer not null default 1000,
  default_easy_pct integer not null default 30,
  default_medium_pct integer not null default 50,
  default_hard_pct integer not null default 20,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  check (default_easy_pct >= 0 and default_medium_pct >= 0 and default_hard_pct >= 0),
  check (default_easy_pct + default_medium_pct + default_hard_pct = 100)
);

create table if not exists public.mcq_subtopics (
  id bigserial primary key,
  topic_id text not null references public.mcq_topics(id) on delete cascade,
  title text not null,
  sort_order integer not null default 0,
  weight_hint numeric not null default 1,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  unique (topic_id, title),
  check (weight_hint > 0)
);

create index if not exists mcq_subtopics_topic_sort_idx
  on public.mcq_subtopics (topic_id, sort_order);

alter table public.mcq_topics enable row level security;
alter table public.mcq_subtopics enable row level security;

create table if not exists public.mcq_questions (
  id uuid primary key default gen_random_uuid(),
  external_id text unique,
  topic_id text not null references public.mcq_topics(id) on delete cascade,
  subtopic_title text not null,
  difficulty text not null check (difficulty in ('easy', 'medium', 'hard')),
  question text not null,
  options jsonb not null,
  answer text not null,
  explanation text,
  source text not null default 'bulk-generator',
  created_at timestamptz not null default now(),
  check (jsonb_typeof(options) = 'array'),
  check (jsonb_array_length(options) = 4)
);

create index if not exists mcq_questions_topic_diff_idx
  on public.mcq_questions (topic_id, difficulty);

create index if not exists mcq_questions_topic_subtopic_idx
  on public.mcq_questions (topic_id, subtopic_title);

alter table public.mcq_questions enable row level security;

drop policy if exists "Public read mcq topics" on public.mcq_topics;
create policy "Public read mcq topics"
  on public.mcq_topics
  for select
  using (true);

drop policy if exists "Public read mcq subtopics" on public.mcq_subtopics;
create policy "Public read mcq subtopics"
  on public.mcq_subtopics
  for select
  using (true);

drop policy if exists "Public read mcq questions" on public.mcq_questions;
create policy "Public read mcq questions"
  on public.mcq_questions
  for select
  using (true);

grant select on table public.mcq_topics to anon, authenticated;
grant select on table public.mcq_subtopics to anon, authenticated;
grant select on table public.mcq_questions to anon, authenticated;

insert into public.mcq_topics (id, title, description, default_questions, default_easy_pct, default_medium_pct, default_hard_pct)
values
  ('computer-networks-cloud', 'Computer Networks and Cloud Computing', 'Networking fundamentals to cloud systems and security.', 1000, 30, 50, 20),
  ('programming-core', 'Programming (C++/Java/Python)', 'Programming foundations, OOP, debugging, and software practices.', 1000, 30, 50, 20),
  ('dsa', 'Data Structures and Algorithms', 'Core and advanced data structures, algorithms, and optimization.', 1000, 30, 50, 20),
  ('operating-systems', 'Operating Systems', 'Process, memory, file systems, and OS-level security.', 1000, 30, 50, 20),
  ('software-engineering', 'Software Engineering', 'Lifecycle, architecture, testing, quality, and risk management.', 1000, 30, 50, 20),
  ('web-development', 'Web Development', 'Frontend, backend, security, APIs, and deployment practices.', 1000, 30, 50, 20),
  ('ai-ml-data-analytics', 'AI / Machine Learning and Data Analytics', 'AI/ML concepts, deep learning, NLP/CV, and MLOps basics.', 1000, 30, 50, 20),
  ('cyber-security', 'Cyber Security', 'Security principles, attack/defense, forensics, and governance.', 1000, 30, 50, 20),
  ('databases', 'Databases', 'Relational systems, SQL, optimization, security, and modern DBs.', 1000, 30, 50, 20),
  ('problem-solving-analytical', 'Problem Solving and Analytical Skills', 'Reasoning, abstraction, algorithmic thinking, and communication.', 1000, 30, 50, 20)
on conflict (id) do update
set
  title = excluded.title,
  description = excluded.description,
  default_questions = excluded.default_questions,
  default_easy_pct = excluded.default_easy_pct,
  default_medium_pct = excluded.default_medium_pct,
  default_hard_pct = excluded.default_hard_pct,
  is_active = true;

insert into public.mcq_subtopics (topic_id, title, sort_order, weight_hint)
values
  ('computer-networks-cloud', 'Data Communication', 1, 1),
  ('computer-networks-cloud', 'Computer Networks', 2, 1),
  ('computer-networks-cloud', 'Data Link Layer', 3, 1),
  ('computer-networks-cloud', 'Network Layer', 4, 1),
  ('computer-networks-cloud', 'Transport Layer', 5, 1),
  ('computer-networks-cloud', 'Application Layer', 6, 1),
  ('computer-networks-cloud', 'Wireless Networks', 7, 1),
  ('computer-networks-cloud', 'Cloud Computing', 8, 1),
  ('computer-networks-cloud', 'Network Security (Networks Perspective)', 9, 1),
  ('computer-networks-cloud', 'Next Generation Networks', 10, 1),

  ('programming-core', 'Programming Fundamentals', 1, 1),
  ('programming-core', 'Data Types & Variables', 2, 1),
  ('programming-core', 'Operators & Expressions', 3, 1),
  ('programming-core', 'Control Structures', 4, 1),
  ('programming-core', 'Functions / Methods', 5, 1),
  ('programming-core', 'Input / Output Handling', 6, 1),
  ('programming-core', 'Strings & Text Processing', 7, 1),
  ('programming-core', 'Arrays & Collections', 8, 1),
  ('programming-core', 'Object-Oriented Programming (OOP)', 9, 1),
  ('programming-core', 'Memory Management Concepts', 10, 1),
  ('programming-core', 'Exception & Error Handling', 11, 1),
  ('programming-core', 'Modules, Packages & Libraries', 12, 1),
  ('programming-core', 'Advanced Programming Concepts', 13, 1),
  ('programming-core', 'Concurrency & Parallelism (Introductory)', 14, 1),
  ('programming-core', 'Debugging, Testing & Optimization', 15, 1),
  ('programming-core', 'Software Development Practices', 16, 1),

  ('dsa', 'Foundations of Data Structure and Algorithms', 1, 1),
  ('dsa', 'Linear Data Structures', 2, 1),
  ('dsa', 'Non-Linear Data Structures', 3, 1),
  ('dsa', 'Searching Algorithms', 4, 1),
  ('dsa', 'Sorting Algorithms', 5, 1),
  ('dsa', 'Hashing', 6, 1),
  ('dsa', 'Tree Algorithms', 7, 1),
  ('dsa', 'Graph Algorithms', 8, 1),
  ('dsa', 'Algorithm Design Techniques', 9, 1),
  ('dsa', 'Advanced Data Structures', 10, 1),
  ('dsa', 'String Algorithms', 11, 1),
  ('dsa', 'Complexity & Optimization', 12, 1),

  ('operating-systems', 'Introduction to Operating Systems', 1, 1),
  ('operating-systems', 'Operating System Structures', 2, 1),
  ('operating-systems', 'Process Management', 3, 1),
  ('operating-systems', 'CPU Scheduling', 4, 1),
  ('operating-systems', 'Thread Management', 5, 1),
  ('operating-systems', 'Concurrency & Synchronization', 6, 1),
  ('operating-systems', 'Deadlocks', 7, 1),
  ('operating-systems', 'Memory Management', 8, 1),
  ('operating-systems', 'File System Management', 9, 1),
  ('operating-systems', 'Secondary Storage Management', 10, 1),
  ('operating-systems', 'Input / Output Systems', 11, 1),
  ('operating-systems', 'Protection & Security', 12, 1),

  ('software-engineering', 'Introduction to Software Engineering', 1, 1),
  ('software-engineering', 'Software Process Models', 2, 1),
  ('software-engineering', 'Agile Software Development', 3, 1),
  ('software-engineering', 'Software Requirements Engineering', 4, 1),
  ('software-engineering', 'Software Project Management', 5, 1),
  ('software-engineering', 'Software Design', 6, 1),
  ('software-engineering', 'Software Architecture', 7, 1),
  ('software-engineering', 'User Interface Design', 8, 1),
  ('software-engineering', 'Software Implementation & Coding', 9, 1),
  ('software-engineering', 'Software Testing', 10, 1),
  ('software-engineering', 'Software Maintenance & Evolution', 11, 1),
  ('software-engineering', 'Software Quality Assurance', 12, 1),
  ('software-engineering', 'Software Metrics & Measurement', 13, 1),
  ('software-engineering', 'Software Configuration Management', 14, 1),
  ('software-engineering', 'Software Risk Management', 15, 1),
  ('software-engineering', 'Software Security Engineering', 16, 1),

  ('web-development', 'Introduction to Web Development', 1, 1),
  ('web-development', 'Web Architecture & Protocols', 2, 1),
  ('web-development', 'HTML Fundamentals', 3, 1),
  ('web-development', 'CSS Fundamentals', 4, 1),
  ('web-development', 'Advanced CSS & Responsive Design', 5, 1),
  ('web-development', 'JavaScript Fundamentals', 6, 1),
  ('web-development', 'Advanced JavaScript', 7, 1),
  ('web-development', 'Frontend Frameworks & Libraries', 8, 1),
  ('web-development', 'Backend Development Fundamentals', 9, 1),
  ('web-development', 'Server-Side Programming', 10, 1),
  ('web-development', 'Databases for Web Applications', 11, 1),
  ('web-development', 'Web Security', 12, 1),
  ('web-development', 'Web Performance & Optimization', 13, 1),
  ('web-development', 'Web Testing & Debugging', 14, 1),
  ('web-development', 'Deployment & Hosting', 15, 1),
  ('web-development', 'Web APIs & Integration', 16, 1),
  ('web-development', 'Modern Web Development Practices', 17, 1),

  ('ai-ml-data-analytics', 'Introduction to AI, ML & Data Analytics', 1, 1),
  ('ai-ml-data-analytics', 'Mathematical Foundations', 2, 1),
  ('ai-ml-data-analytics', 'Python for AI & Data Analytics', 3, 1),
  ('ai-ml-data-analytics', 'Data Collection & Pre-processing', 4, 1),
  ('ai-ml-data-analytics', 'Exploratory Data Analysis (EDA)', 5, 1),
  ('ai-ml-data-analytics', 'Supervised Learning', 6, 1),
  ('ai-ml-data-analytics', 'Ensemble Learning', 7, 1),
  ('ai-ml-data-analytics', 'Unsupervised Learning', 8, 1),
  ('ai-ml-data-analytics', 'Model Evaluation & Validation', 9, 1),
  ('ai-ml-data-analytics', 'Feature Engineering & Selection', 10, 1),
  ('ai-ml-data-analytics', 'Deep Learning Fundamentals', 11, 1),
  ('ai-ml-data-analytics', 'Advanced Deep Learning', 12, 1),
  ('ai-ml-data-analytics', 'Natural Language Processing (NLP)', 13, 1),
  ('ai-ml-data-analytics', 'Computer Vision', 14, 1),
  ('ai-ml-data-analytics', 'Big Data Analytics (Introductory)', 15, 1),
  ('ai-ml-data-analytics', 'Model Deployment & MLOps Basics', 16, 1),
  ('ai-ml-data-analytics', 'AI Ethics, Security & Privacy', 17, 1),

  ('cyber-security', 'Introduction to Cyber Security', 1, 1),
  ('cyber-security', 'Security Fundamentals & Principles', 2, 1),
  ('cyber-security', 'Cryptography Basics', 3, 1),
  ('cyber-security', 'Network Security', 4, 1),
  ('cyber-security', 'Operating System Security', 5, 1),
  ('cyber-security', 'Web Application Security', 6, 1),
  ('cyber-security', 'Malware & Attack Techniques', 7, 1),
  ('cyber-security', 'Authentication & Access Control', 8, 1),
  ('cyber-security', 'Secure Software Development', 9, 1),
  ('cyber-security', 'Wireless & Mobile Security', 10, 1),
  ('cyber-security', 'Cloud & Virtualization Security', 11, 1),
  ('cyber-security', 'Digital Forensics', 12, 1),
  ('cyber-security', 'Incident Response & Management', 13, 1),
  ('cyber-security', 'Security Monitoring & Auditing', 14, 1),
  ('cyber-security', 'Cyber Laws & Ethics', 15, 1),
  ('cyber-security', 'Emerging Trends in Cyber Security', 16, 1),

  ('databases', 'Introduction to Database Systems', 1, 1),
  ('databases', 'Database System Architecture', 2, 1),
  ('databases', 'Data Models', 3, 1),
  ('databases', 'Relational Database Concepts', 4, 1),
  ('databases', 'Relational Algebra & Calculus', 5, 1),
  ('databases', 'Structured Query Language (SQL)', 6, 1),
  ('databases', 'Advanced SQL', 7, 1),
  ('databases', 'Database Design & Normalization', 8, 1),
  ('databases', 'Transaction Management', 9, 1),
  ('databases', 'Concurrency Control', 10, 1),
  ('databases', 'Recovery Management', 11, 1),
  ('databases', 'Indexing & File Organization', 12, 1),
  ('databases', 'Query Processing & Optimization', 13, 1),
  ('databases', 'Database Security', 14, 1),
  ('databases', 'Distributed Databases', 15, 1),
  ('databases', 'NoSQL & Modern Databases', 16, 1),
  ('databases', 'Data Warehousing & Data Mining (Introductory)', 17, 1),

  ('problem-solving-analytical', 'Introduction to Problem Solving', 1, 1),
  ('problem-solving-analytical', 'Problem Understanding & Analysis', 2, 1),
  ('problem-solving-analytical', 'Logical Reasoning Fundamentals', 3, 1),
  ('problem-solving-analytical', 'Algorithms & Flow Control', 4, 1),
  ('problem-solving-analytical', 'Data Representation & Abstraction', 5, 1),
  ('problem-solving-analytical', 'Pattern Recognition & Generalization', 6, 1),
  ('problem-solving-analytical', 'Mathematical & Quantitative Reasoning', 7, 1),
  ('problem-solving-analytical', 'Algorithmic Thinking', 8, 1),
  ('problem-solving-analytical', 'Critical Thinking & Decision Making', 9, 1),
  ('problem-solving-analytical', 'Debugging & Error Analysis', 10, 1),
  ('problem-solving-analytical', 'Complexity & Efficiency Awareness', 11, 1),
  ('problem-solving-analytical', 'Problem Solving Using Programming', 12, 1),
  ('problem-solving-analytical', 'Data-Driven Problem Solving', 13, 1),
  ('problem-solving-analytical', 'Creative & Innovative Thinking', 14, 1),
  ('problem-solving-analytical', 'Real-World Problem Solving', 15, 1),
  ('problem-solving-analytical', 'Communication & Documentation of Solutions', 16, 1)
on conflict (topic_id, title) do update
set
  sort_order = excluded.sort_order,
  weight_hint = excluded.weight_hint,
  is_active = true;
