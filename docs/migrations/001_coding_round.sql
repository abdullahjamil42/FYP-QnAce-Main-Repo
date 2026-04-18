-- Incremental migration: live coding round (idempotent; safe to re-run)
-- Apply with: psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f docs/migrations/001_coding_round.sql

-- Scoring blob from POST /api/interview/submit
ALTER TABLE public.interview_sessions
  ADD COLUMN IF NOT EXISTS coding_round jsonb;

-- LeetCode-style problems
CREATE TABLE IF NOT EXISTS public.problems (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  external_slug text UNIQUE,
  title text NOT NULL,
  difficulty text NOT NULL DEFAULT 'medium',
  topics jsonb NOT NULL DEFAULT '[]'::jsonb,
  description text NOT NULL DEFAULT '',
  examples jsonb NOT NULL DEFAULT '[]'::jsonb,
  constraints text NOT NULL DEFAULT '',
  hints jsonb NOT NULL DEFAULT '[]'::jsonb,
  complexity_benchmark_stdin jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS problems_difficulty_idx ON public.problems (difficulty);

CREATE TABLE IF NOT EXISTS public.test_cases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  problem_id uuid NOT NULL REFERENCES public.problems(id) ON DELETE CASCADE,
  stdin text NOT NULL DEFAULT '',
  expected_output text NOT NULL DEFAULT '',
  is_hidden boolean NOT NULL DEFAULT false,
  sort_order integer NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS test_cases_problem_idx ON public.test_cases (problem_id, is_hidden, sort_order);

ALTER TABLE public.problems ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.test_cases ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public read problems" ON public.problems;
CREATE POLICY "Public read problems"
  ON public.problems
  FOR SELECT
  USING (true);

DROP POLICY IF EXISTS "Public read non-hidden test cases" ON public.test_cases;
CREATE POLICY "Public read non-hidden test cases"
  ON public.test_cases
  FOR SELECT
  USING (is_hidden = false);

GRANT SELECT ON TABLE public.problems TO anon, authenticated;
GRANT SELECT ON TABLE public.test_cases TO anon, authenticated;
