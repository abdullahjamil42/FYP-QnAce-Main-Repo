-- Migration 006: per_question_scores column on interview_sessions
-- Stores the question-by-question score breakdown captured during the live
-- interview (used by /reports and /session/summary).
-- Run in Supabase SQL editor.

alter table public.interview_sessions
  add column if not exists per_question_scores jsonb not null default '[]'::jsonb;
