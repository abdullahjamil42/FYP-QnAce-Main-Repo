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
